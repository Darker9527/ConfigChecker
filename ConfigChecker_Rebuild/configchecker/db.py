# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import text
from .models import SysConfig

DEFAULT_DB = Path(__file__).resolve().parents[1] / 'data.db'


def engine(db_path: str | Path = DEFAULT_DB):
    return create_engine(f"sqlite:///{Path(db_path)}", echo=False)


def _ensure_column(eng, table: str, column: str, ddl: str):
    with eng.connect() as conn:
        cols = [r[1] for r in conn.execute(text(f'PRAGMA table_info({table})')).fetchall()]
        if column not in cols:
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {ddl}'))
            conn.commit()


def init_db(db_path: str | Path = DEFAULT_DB):
    eng = engine(db_path)
    SQLModel.metadata.create_all(eng)
    # 兼容旧版 data.db：create_all 不会给既有表自动加列。
    _ensure_column(eng, 'checktask', 'asset_id', 'asset_id INTEGER')
    _ensure_column(eng, 'checktask', 'score', 'score FLOAT')
    with Session(eng) as session:
        defaults = {
            'out_path': str(Path(__file__).resolve().parents[1] / 'reports'),
            'debug': '0',
            'ai_enabled': '0',
            'ai_base_url': '',
            'ai_model': '',
            'ai_api_key': '',
        }
        for k, v in defaults.items():
            if not session.get(SysConfig, k):
                session.add(SysConfig(config=k, value=v))
        session.commit()
    return eng


def get_config(session: Session, key: str, default: str = '') -> str:
    row = session.get(SysConfig, key)
    return row.value if row else default


def set_config(session: Session, key: str, value: str):
    row = session.get(SysConfig, key)
    if row:
        row.value = value
    else:
        session.add(SysConfig(config=key, value=value))
