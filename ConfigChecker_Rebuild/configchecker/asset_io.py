# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime
from sqlmodel import Session, select
from .models import Asset

FIELDS = ['name', 'ip', 'hostname', 'devtype', 'brand', 'owner', 'department', 'importance', 'tags']


def import_assets_csv(session: Session, path: str | Path) -> tuple[int, int]:
    inserted = skipped = 0
    with Path(path).open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get('name') or row.get('hostname') or row.get('ip') or '').strip()
            devtype = (row.get('devtype') or '').strip()
            brand = (row.get('brand') or '通用').strip()
            if not name or not devtype:
                skipped += 1
                continue
            exists = session.exec(select(Asset).where(Asset.name == name)).first()
            if exists:
                skipped += 1
                continue
            session.add(Asset(
                name=name,
                ip=(row.get('ip') or '').strip(),
                hostname=(row.get('hostname') or '').strip(),
                devtype=devtype,
                brand=brand,
                owner=(row.get('owner') or '').strip(),
                department=(row.get('department') or '').strip(),
                importance=(row.get('importance') or '一般').strip(),
                tags=(row.get('tags') or '').strip(),
            ))
            inserted += 1
    session.commit()
    return inserted, skipped


def export_assets_csv(session: Session, path: str | Path) -> int:
    rows = session.exec(select(Asset).order_by(Asset.id)).all()
    with Path(path).open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id'] + FIELDS + ['created_at', 'updated_at'])
        writer.writeheader()
        for a in rows:
            writer.writerow({k: getattr(a, k) for k in ['id'] + FIELDS + ['created_at', 'updated_at']})
    return len(rows)
