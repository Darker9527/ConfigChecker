# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3
from pathlib import Path
from sqlmodel import Session, select
from .models import Baseline


def migrate_original_db(session: Session, original_db: str | Path) -> tuple[int, int]:
    """从原 ConfigChecker data.db 迁移 baseline 到重建版。

    原库字段：name, descr, reference, content, mtime, devtype, brand, chktype, cmd
    重建版新增 risk/level：从 descr/content 中尽量推断。
    """
    original_db = Path(original_db)
    if not original_db.exists():
        raise FileNotFoundError(f'原数据库不存在：{original_db}')

    conn = sqlite3.connect(str(original_db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT name, descr, reference, content, mtime, devtype, brand, chktype, cmd FROM baseline"
    ).fetchall()
    conn.close()

    existing = {
        (r.devtype, r.brand, r.name)
        for r in session.exec(select(Baseline)).all()
        if r.name
    }
    inserted = 0
    skipped = 0
    for r in rows:
        name = (r['name'] or r['descr'] or '').strip()
        devtype = (r['devtype'] or '').strip()
        brand = (r['brand'] or '通用').strip()
        content = (r['content'] or '').strip()
        if not name or not devtype or not content:
            skipped += 1
            continue
        key = (devtype, brand, name)
        if key in existing:
            skipped += 1
            continue
        text = f"{r['descr'] or ''} {content}"
        risk = '高风险' if any(x in text for x in ['高风险', '双因素', '弱口令', '默认口令', '未授权', '明文', 'any-any']) else '中风险'
        level = '三级' if '三级' in text else '二级/三级'
        session.add(Baseline(
            name=name,
            descr=(r['descr'] or name).strip(),
            reference=(r['reference'] or '').strip() or None,
            content=content,
            mtime=(r['mtime'] or '').strip() or None,
            devtype=devtype,
            brand=brand,
            chktype=(r['chktype'] or '1').strip(),
            cmd=(r['cmd'] or '').strip() or None,
            risk=risk,
            level=level,
        ))
        existing.add(key)
        inserted += 1
    session.commit()
    return inserted, skipped
