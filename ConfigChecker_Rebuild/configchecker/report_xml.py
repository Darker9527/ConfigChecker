# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree
from .models import CheckTask, CheckResult


def write_xml_report(task: CheckTask, results: list[CheckResult], out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f'{task.name}_{task.id or "new"}.xml'

    root = Element('config_check_report')
    meta = SubElement(root, 'task')
    for key, value in {
        'id': task.id,
        'name': task.name,
        'devtype': task.devtype,
        'brand': task.brand,
        'config_path': task.config_path,
        'created_at': task.created_at,
    }.items():
        node = SubElement(meta, key)
        node.text = '' if value is None else str(value)

    summary = SubElement(root, 'summary')
    counts = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    for status, count in counts.items():
        item = SubElement(summary, 'status')
        item.set('name', status)
        item.set('count', str(count))

    items = SubElement(root, 'results')
    for r in results:
        item = SubElement(items, 'result')
        for key, value in {
            'baseline_name': r.baseline_name,
            'status': r.status,
            'risk': r.risk,
            'evidence': r.evidence,
            'reason': r.reason,
            'suggestion': r.suggestion,
        }.items():
            node = SubElement(item, key)
            node.text = value or ''

    ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)
    return path
