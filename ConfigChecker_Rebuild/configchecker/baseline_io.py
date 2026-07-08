# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
from pathlib import Path
from sqlmodel import Session, select
from .models import Baseline

FIELDS = ['name', 'descr', 'reference', 'content', 'devtype', 'brand', 'chktype', 'cmd', 'risk', 'level']


def import_baseline_csv(session: Session, path: str | Path) -> tuple[int, int]:
    inserted = 0
    skipped = 0
    with Path(path).open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not any((v or '').strip() for v in row.values()):
                continue
            name = (row.get('name') or '').strip()
            devtype = (row.get('devtype') or '').strip()
            brand = (row.get('brand') or '').strip()
            if not name or not devtype or not brand:
                continue
            exists = session.exec(
                select(Baseline).where(
                    Baseline.name == name,
                    Baseline.devtype == devtype,
                    Baseline.brand == brand,
                )
            ).first()
            if exists:
                skipped += 1
                continue
            session.add(Baseline(
                name=name,
                descr=(row.get('descr') or name).strip(),
                reference=(row.get('reference') or '').strip() or None,
                content=(row.get('content') or '').strip(),
                devtype=devtype,
                brand=brand,
                chktype=(row.get('chktype') or '1').strip(),
                cmd=(row.get('cmd') or '').strip() or None,
                risk=(row.get('risk') or '中风险').strip(),
                level=(row.get('level') or '二级/三级').strip(),
            ))
            inserted += 1
    session.commit()
    return inserted, skipped


def export_baseline_csv(session: Session, path: str | Path) -> int:
    rows = session.exec(select(Baseline).order_by(Baseline.devtype, Baseline.brand, Baseline.name)).all()
    with Path(path).open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for b in rows:
            writer.writerow({k: getattr(b, k) for k in FIELDS})
    return len(rows)
