# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from .models import CheckTask, CheckResult


def write_markdown_remediation(task: CheckTask, results: list[CheckResult], out_dir: str | Path, only_failed: bool = True) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f'{task.name}_{task.id or "new"}_整改台账.md'
    selected = [r for r in results if (not only_failed or r.status == '未通过')]
    risk_order = {'高风险': 0, '中风险': 1, '低风险': 2}
    selected.sort(key=lambda r: (risk_order.get(r.risk, 9), r.baseline_name))
    lines = [
        f'# {task.name} 整改台账',
        '',
        f'- 设备类型：{task.devtype}',
        f'- 设备品牌：{task.brand}',
        f'- 配置文件：`{task.config_path}`',
        f'- 待整改项：{len(selected)}',
        '',
        '| 序号 | 风险 | 检查项 | 状态 | 问题原因 | 整改建议 | 证据 | 责任人 | 计划完成时间 | 整改状态 |',
        '|---:|---|---|---|---|---|---|---|---|---|',
    ]
    for i, r in enumerate(selected, 1):
        def esc(v: str) -> str:
            return (v or '').replace('|', '\\|').replace('\n', '<br>')
        lines.append(
            f'| {i} | {esc(r.risk)} | {esc(r.baseline_name)} | {esc(r.status)} | '
            f'{esc(r.reason)} | {esc(r.suggestion)} | {esc(r.evidence)} |  |  | 未整改 |'
        )
    path.write_text('\n'.join(lines), encoding='utf-8')
    return path
