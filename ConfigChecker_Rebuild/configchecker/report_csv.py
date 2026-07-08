# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
from pathlib import Path
from .models import CheckTask, CheckResult

FIELDS = ['task_id', 'task_name', 'devtype', 'brand', 'baseline_name', 'status', 'risk', 'evidence', 'reason', 'suggestion']


def write_csv_report(task: CheckTask, results: list[CheckResult], out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f'{task.name}_{task.id or "new"}.csv'
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in results:
            writer.writerow({
                'task_id': task.id,
                'task_name': task.name,
                'devtype': task.devtype,
                'brand': task.brand,
                'baseline_name': r.baseline_name,
                'status': r.status,
                'risk': r.risk,
                'evidence': r.evidence,
                'reason': r.reason,
                'suggestion': r.suggestion,
            })
    return path
