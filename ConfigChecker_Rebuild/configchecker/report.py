# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from collections import Counter
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .models import CheckTask, CheckResult

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / 'templates'


def write_html_report(task: CheckTask, results: list[CheckResult], out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(['html', 'xml'])
    )
    tpl = env.get_template('report.html')
    summary = dict(Counter(r.status for r in results))
    html = tpl.render(task=task, results=results, summary=summary)
    report_path = out / f'{task.name}_{task.id or "new"}.html'
    report_path.write_text(html, encoding='utf-8')
    return report_path
