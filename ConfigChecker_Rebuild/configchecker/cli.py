# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from sqlmodel import Session, select

from .db import DEFAULT_DB, engine, init_db, get_config, set_config
from .models import Baseline, CheckTask, CheckResult, SysConfig, Asset, ExceptionItem
from .checker import rule_check
from .ai import ai_check_openai_compatible
from .baseline_io import import_baseline_csv, export_baseline_csv
from .report import write_html_report
from .report_csv import write_csv_report
from .migrate import migrate_original_db
from .remediation import write_markdown_remediation
from .identify import identify_file
from .asset_io import import_assets_csv, export_assets_csv


def force_utf8():
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, 'reconfigure'):
            s.reconfigure(encoding='utf-8', errors='replace')


def cmd_init_db(args):
    init_db(args.db)
    print(f'数据库已初始化：{args.db}')


def cmd_summary(args):
    eng = init_db(args.db)
    with Session(eng) as session:
        total = len(session.exec(select(Baseline)).all())
        print(f'数据库：{args.db}')
        print(f'基线数量：{total}')
        rows = session.exec(select(Baseline.devtype, Baseline.brand)).all()
        counter = {}
        for devtype, brand in rows:
            counter[(devtype, brand)] = counter.get((devtype, brand), 0) + 1
        for (devtype, brand), n in sorted(counter.items(), key=lambda x: (-x[1], x[0])):
            print(f'- {devtype} / {brand}: {n}')


def cmd_import_baseline(args):
    eng = init_db(args.db)
    with Session(eng) as session:
        inserted, skipped = import_baseline_csv(session, args.csv)
    print(f'导入完成：新增 {inserted}，跳过重复 {skipped}')


def cmd_import_assets(args):
    eng = init_db(args.db)
    with Session(eng) as session:
        inserted, skipped = import_assets_csv(session, args.csv)
    print(f'资产导入完成：新增 {inserted}，跳过 {skipped}')


def cmd_export_assets(args):
    eng = init_db(args.db)
    with Session(eng) as session:
        count = export_assets_csv(session, args.csv)
    print(f'已导出资产 {count} 条：{args.csv}')


def cmd_assets(args):
    eng = init_db(args.db)
    with Session(eng) as session:
        rows = session.exec(select(Asset).order_by(Asset.id.desc()).limit(args.limit)).all()
        for a in rows:
            print(f'#{a.id} {a.name} {a.ip} {a.devtype}/{a.brand} owner={a.owner} dept={a.department} importance={a.importance}')


def cmd_add_asset(args):
    eng = init_db(args.db)
    with Session(eng) as session:
        a = Asset(name=args.name, ip=args.ip or '', hostname=args.hostname or '', devtype=args.devtype, brand=args.brand, owner=args.owner or '', department=args.department or '', importance=args.importance, tags=args.tags or '')
        session.add(a)
        session.commit()
        session.refresh(a)
        print(f'已新增资产 #{a.id}: {a.name}')


def cmd_export_baseline(args):
    eng = init_db(args.db)
    with Session(eng) as session:
        count = export_baseline_csv(session, args.csv)
    print(f'已导出 {count} 条：{args.csv}')


def load_baselines(session: Session, devtype: str, brand: str, min_risk: str | None = None):
    rows = session.exec(
        select(Baseline).where(
            Baseline.devtype == devtype,
            Baseline.brand.in_([brand, '通用'])
        ).order_by(Baseline.brand, Baseline.name)
    ).all()
    if min_risk:
        order = {'低风险': 1, '中风险': 2, '高风险': 3}
        threshold = order.get(min_risk, 0)
        rows = [r for r in rows if order.get(r.risk, 2) >= threshold]
    return rows


def risk_score(results: list[CheckResult]) -> float:
    weights = {'高风险': 5, '中风险': 3, '低风险': 1}
    total = sum(weights.get(r.risk, 3) for r in results) or 1
    penalty = sum(weights.get(r.risk, 3) for r in results if r.status == '未通过')
    return round(max(0, 100 * (1 - penalty / total)), 2)


def is_exception_active(session: Session, asset_id: int | None, baseline_id: int) -> ExceptionItem | None:
    today = __import__('datetime').datetime.now().strftime('%Y-%m-%d')
    rows = session.exec(select(ExceptionItem).where(ExceptionItem.baseline_id == baseline_id, ExceptionItem.status == '有效')).all()
    for e in rows:
        if e.asset_id not in (None, asset_id):
            continue
        if e.expire_at and e.expire_at < today:
            continue
        return e
    return None


def run_check(session: Session, config_path: Path, devtype: str, brand: str, name: str, mode: str = 'rule', formats: str = 'html', asset_id: int | None = None, min_risk: str | None = None):
    text = config_path.read_text(encoding='utf-8', errors='ignore')
    baselines = load_baselines(session, devtype, brand, min_risk)
    task = CheckTask(name=name, devtype=devtype, brand=brand, config_path=str(config_path), asset_id=asset_id)
    session.add(task)
    session.commit()
    session.refresh(task)
    results = []
    ai_base_url = get_config(session, 'ai_base_url')
    ai_api_key = get_config(session, 'ai_api_key')
    ai_model = get_config(session, 'ai_model')
    ai_workers = int(get_config(session, 'ai_workers', '1') or '1')
    ai_retries = int(get_config(session, 'ai_retries', '2') or '2')

    def evaluate(b):
        d = rule_check(text, b.content, b.cmd)
        if mode in {'ai', 'hybrid'}:
            should_call_ai = mode == 'ai' or d.status in {'需复核', '未通过'}
            if should_call_ai:
                try:
                    d = ai_check_openai_compatible(
                        base_url=ai_base_url,
                        api_key=ai_api_key,
                        model=ai_model,
                        config_text=text,
                        baseline_name=b.name,
                        baseline_content=b.content,
                        evidence_hint=d.evidence,
                        retries=ai_retries,
                    )
                except Exception as e:
                    d.reason = f'{d.reason}\nAI 判定失败：{e!r}'
        return b, d

    if mode in {'ai', 'hybrid'} and ai_workers > 1:
        evaluated = []
        with ThreadPoolExecutor(max_workers=ai_workers) as ex:
            future_map = {ex.submit(evaluate, b): b for b in baselines}
            for fut in as_completed(future_map):
                evaluated.append(fut.result())
        evaluated.sort(key=lambda x: x[0].name)
    else:
        evaluated = [evaluate(b) for b in baselines]

    for b, d in evaluated:
        exc = is_exception_active(session, asset_id, b.id)
        if exc:
            d.status = '不适用'
            d.reason = f'命中有效例外：{exc.reason}；批准人：{exc.approved_by}；到期：{exc.expire_at}'
        r = CheckResult(
            task_id=task.id,
            baseline_id=b.id,
            baseline_name=b.name,
            status=d.status,
            risk=b.risk,
            evidence=d.evidence,
            suggestion=d.suggestion,
            reason=d.reason,
        )
        session.add(r)
        results.append(r)
    session.commit()
    out_dir = get_config(session, 'out_path', str(Path.cwd() / 'reports'))
    report_paths = []
    requested = {x.strip().lower() for x in formats.split(',') if x.strip()}
    if 'html' in requested:
        report_paths.append(write_html_report(task, results, out_dir))
    if 'csv' in requested:
        report_paths.append(write_csv_report(task, results, out_dir))
    if 'xlsx' in requested:
        from .report_xlsx import write_xlsx_report
        report_paths.append(write_xlsx_report(task, results, out_dir))
    if 'excel' in requested:
        from .report_xlsx import write_xlsx_report
        report_paths.append(write_xlsx_report(task, results, out_dir))
    if 'docx' in requested or 'word' in requested:
        from .report_docx import write_docx_report
        report_paths.append(write_docx_report(task, results, out_dir))
    if 'pdf' in requested:
        from .report_pdf import write_pdf_report
        report_paths.append(write_pdf_report(task, results, out_dir))
    if 'xml' in requested:
        from .report_xml import write_xml_report
        report_paths.append(write_xml_report(task, results, out_dir))
    if 'json' in requested:
        from .report_json import write_json_report
        report_paths.append(write_json_report(task, results, out_dir))
    if 'remediation' in requested or 'md' in requested:
        report_paths.append(write_markdown_remediation(task, results, out_dir))
    if 'remediation-xlsx' in requested or '整改台账' in requested:
        from .remediation_xlsx import write_remediation_xlsx
        report_paths.append(write_remediation_xlsx(task, results, out_dir))
    task.score = risk_score(results)
    task.report_path = ';'.join(str(p) for p in report_paths)
    session.add(task)
    session.commit()
    return task, results, report_paths


def cmd_check(args):
    eng = init_db(args.db)
    devtype, brand = args.devtype, args.brand
    if args.auto:
        devtype, brand, scores = identify_file(args.config)
        print(f'自动识别：{devtype} / {brand}  候选：{scores}')
    with Session(eng) as session:
        task, results, reports = run_check(session, Path(args.config), devtype, brand, args.name, args.mode, args.format, args.asset_id, args.min_risk)
    print(f'检查完成：{len(results)} 项')
    print(f'合规评分：{task.score}')
    if args.ci and any(r.status == '未通过' and (not args.min_risk or r.risk == args.min_risk or args.min_risk == '低风险') for r in results):
        for report in reports:
            print(f'报告：{report}')
        raise SystemExit(1)
    for report in reports:
        print(f'报告：{report}')


def cmd_batch(args):
    eng = init_db(args.db)
    config_dir = Path(args.directory)
    files = [p for p in config_dir.iterdir() if p.is_file()]
    if args.workers > 1 and not args.auto:
        from .batch import run_batch_parallel
        for filename, count, reports in run_batch_parallel(args.db, args.directory, args.devtype, args.brand, args.name, args.mode, args.format, args.workers):
            print(f'{filename}: {count} 项 -> {"; ".join(str(r) for r in reports)}')
        return
    with Session(eng) as session:
        for p in files:
            task_name = f'{args.name}_{p.stem}'
            devtype, brand = args.devtype, args.brand
            if args.auto:
                devtype, brand, _ = identify_file(p)
            _, results, reports = run_check(session, p, devtype, brand, task_name, args.mode, args.format)
            print(f'{p.name} ({devtype}/{brand}): {len(results)} 项 -> {"; ".join(str(r) for r in reports)}')


def cmd_config(args):
    eng = init_db(args.db)
    with Session(eng) as session:
        if args.action == 'list':
            for row in session.exec(select(SysConfig).order_by(SysConfig.config)).all():
                value = row.value
                if 'key' in row.config.lower() and value:
                    value = value[:4] + '***'
                print(f'{row.config}={value}')
        elif args.action == 'set':
            set_config(session, args.key, args.value)
            session.commit()
            print(f'已设置：{args.key}')
        else:
            raise SystemExit('未知 config action')


def cmd_tasks(args):
    eng = init_db(args.db)
    with Session(eng) as session:
        tasks = session.exec(select(CheckTask).order_by(CheckTask.id.desc()).limit(args.limit)).all()
        for t in tasks:
            print(f'#{t.id} {t.created_at} {t.name} {t.devtype}/{t.brand} -> {t.report_path or "未生成"}')


def cmd_delete_task(args):
    eng = init_db(args.db)
    with Session(eng) as session:
        task = session.get(CheckTask, args.task_id)
        if not task:
            raise SystemExit(f'任务不存在：{args.task_id}')
        results = session.exec(select(CheckResult).where(CheckResult.task_id == args.task_id)).all()
        for r in results:
            session.delete(r)
        session.delete(task)
        session.commit()
        print(f'已删除任务 #{args.task_id} 及结果 {len(results)} 条')


def cmd_cleanup_tasks(args):
    eng = init_db(args.db)
    with Session(eng) as session:
        tasks = session.exec(select(CheckTask).order_by(CheckTask.id.desc())).all()
        keep = set(t.id for t in tasks[:args.keep])
        deleted_tasks = 0
        deleted_results = 0
        for t in tasks:
            if t.id in keep:
                continue
            results = session.exec(select(CheckResult).where(CheckResult.task_id == t.id)).all()
            for r in results:
                session.delete(r)
                deleted_results += 1
            session.delete(t)
            deleted_tasks += 1
        session.commit()
        print(f'已清理任务 {deleted_tasks} 个，结果 {deleted_results} 条，保留最近 {args.keep} 个任务')


def cmd_migrate_original(args):
    eng = init_db(args.db)
    with Session(eng) as session:
        inserted, skipped = migrate_original_db(session, args.original_db)
    print(f'迁移完成：新增 {inserted}，跳过 {skipped}')


def cmd_task_detail(args):
    eng = init_db(args.db)
    with Session(eng) as session:
        task = session.get(CheckTask, args.task_id)
        if not task:
            raise SystemExit(f'任务不存在：{args.task_id}')
        print(f'任务：#{task.id} {task.name} {task.devtype}/{task.brand}')
        print(f'配置：{task.config_path}')
        print(f'报告：{task.report_path or "未生成"}')
        results = session.exec(select(CheckResult).where(CheckResult.task_id == args.task_id)).all()
        for r in results:
            print(f'\n[{r.status}] {r.risk} {r.baseline_name}')
            print(f'证据：{r.evidence}')
            print(f'原因：{r.reason}')
            print(f'建议：{r.suggestion}')


def cmd_remediation(args):
    eng = init_db(args.db)
    with Session(eng) as session:
        task = session.get(CheckTask, args.task_id)
        if not task:
            raise SystemExit(f'任务不存在：{args.task_id}')
        results = session.exec(select(CheckResult).where(CheckResult.task_id == args.task_id)).all()
        out_dir = args.out or get_config(session, 'out_path', str(Path.cwd() / 'reports'))
        if args.format in {'xlsx', 'excel'}:
            from .remediation_xlsx import write_remediation_xlsx
            path = write_remediation_xlsx(task, results, out_dir, only_failed=not args.all)
        else:
            path = write_markdown_remediation(task, results, out_dir, only_failed=not args.all)
        print(f'整改台账：{path}')


def build_parser():
    p = argparse.ArgumentParser(prog='configchecker', description='ConfigChecker Rebuild CLI')
    p.add_argument('--db', default=str(DEFAULT_DB), help='SQLite 数据库路径')
    sub = p.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('init-db', help='初始化数据库')
    s.set_defaults(func=cmd_init_db)

    s = sub.add_parser('summary', help='查看基线汇总')
    s.set_defaults(func=cmd_summary)

    s = sub.add_parser('import-baseline', help='导入基线 CSV')
    s.add_argument('csv')
    s.set_defaults(func=cmd_import_baseline)

    s = sub.add_parser('export-baseline', help='导出基线 CSV')
    s.add_argument('csv')
    s.set_defaults(func=cmd_export_baseline)

    s = sub.add_parser('check', help='检查单个配置文件')
    s.add_argument('config')
    s.add_argument('--devtype', default=None)
    s.add_argument('--brand', default=None)
    s.add_argument('--auto', action='store_true', help='自动识别设备类型/品牌')
    s.add_argument('--name', default='check-task')
    s.add_argument('--mode', choices=['rule', 'ai', 'hybrid'], default='rule', help='判定模式：rule=规则证据检索，ai=全量AI，hybrid=规则+AI复核')
    s.add_argument('--format', default='html', help='报告格式，逗号分隔：html,csv')
    s.set_defaults(func=cmd_check)

    s = sub.add_parser('batch', help='批量检查目录内配置文件')
    s.add_argument('directory')
    s.add_argument('--devtype', default=None)
    s.add_argument('--brand', default=None)
    s.add_argument('--auto', action='store_true', help='自动识别每个文件的设备类型/品牌')
    s.add_argument('--name', default='batch-task')
    s.add_argument('--mode', choices=['rule', 'ai', 'hybrid'], default='rule')
    s.add_argument('--format', default='html')
    s.add_argument('--workers', type=int, default=1, help='并发线程数，默认 1')
    s.set_defaults(func=cmd_batch)

    s = sub.add_parser('config', help='查看或设置配置')
    cfg_sub = s.add_subparsers(dest='action', required=True)
    c = cfg_sub.add_parser('list', help='列出配置')
    c.set_defaults(func=cmd_config)
    c = cfg_sub.add_parser('set', help='设置配置项')
    c.add_argument('key')
    c.add_argument('value')
    c.set_defaults(func=cmd_config)

    s = sub.add_parser('tasks', help='查看历史任务')
    s.add_argument('--limit', type=int, default=20)
    s.set_defaults(func=cmd_tasks)

    s = sub.add_parser('delete-task', help='删除任务及其检查结果')
    s.add_argument('task_id', type=int)
    s.set_defaults(func=cmd_delete_task)

    s = sub.add_parser('cleanup-tasks', help='清理历史任务，仅保留最近 N 个')
    s.add_argument('--keep', type=int, default=50)
    s.set_defaults(func=cmd_cleanup_tasks)

    s = sub.add_parser('task-detail', help='查看任务详情')
    s.add_argument('task_id', type=int)
    s.set_defaults(func=cmd_task_detail)

    s = sub.add_parser('remediation', help='为任务生成整改台账 Markdown/Excel')
    s.add_argument('task_id', type=int)
    s.add_argument('--out', default=None, help='输出目录，默认 out_path')
    s.add_argument('--format', choices=['md', 'xlsx', 'excel'], default='md')
    s.add_argument('--all', action='store_true', help='包含所有状态，默认只导出未通过')
    s.set_defaults(func=cmd_remediation)

    s = sub.add_parser('migrate-original', help='从原 ConfigChecker data.db 迁移 baseline')
    s.add_argument('original_db')
    s.set_defaults(func=cmd_migrate_original)
    return p


def main():
    force_utf8()
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
