# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from sqlmodel import Session, select
from .db import init_db
from .models import Asset, CheckTask, CheckResult, ExceptionItem
from .cli import run_check, risk_score


def asset_summary(db_path: str, asset_id: int):
    eng = init_db(db_path)
    with Session(eng) as session:
        asset = session.get(Asset, asset_id)
        if not asset:
            raise ValueError(f'资产不存在：{asset_id}')
        tasks = session.exec(select(CheckTask).where(CheckTask.asset_id == asset_id).order_by(CheckTask.id.desc())).all()
        latest = tasks[0] if tasks else None
        latest_results = []
        if latest:
            latest_results = session.exec(select(CheckResult).where(CheckResult.task_id == latest.id)).all()
        return asset, tasks, latest, latest_results
