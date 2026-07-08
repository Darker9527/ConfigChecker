# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from .models import CheckTask, CheckResult


def write_json_report(task: CheckTask, results: list[CheckResult], out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f'{task.name}_{task.id or "new"}.json'
    counts = {}
    risks = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
        risks[r.risk] = risks.get(r.risk, 0) + 1
    data = {
        'task': {
            'id': task.id,
            'name': task.name,
            'devtype': task.devtype,
            'brand': task.brand,
            'asset_id': task.asset_id,
            'config_path': task.config_path,
            'score': task.score,
            'created_at': task.created_at,
        },
        'summary': {'status': counts, 'risk': risks},
        'results': [
            {
                'baseline_id': r.baseline_id,
                'baseline_name': r.baseline_name,
                'status': r.status,
                'risk': r.risk,
                'evidence': r.evidence,
                'reason': r.reason,
                'suggestion': r.suggestion,
            }
            for r in results
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return path
