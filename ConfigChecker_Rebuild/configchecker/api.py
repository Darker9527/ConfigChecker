# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from .db import DEFAULT_DB, init_db
from .models import CheckTask
from .cli import run_check
from .identify import identify_file

app = FastAPI(title='ConfigChecker Rebuild API', version='0.1.0')
UPLOAD_DIR = Path(__file__).resolve().parents[1] / 'uploads'


@app.on_event('startup')
def startup():
    init_db(DEFAULT_DB)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/checks')
async def create_check(
    file: UploadFile = File(...),
    devtype: str | None = Form(None),
    brand: str | None = Form(None),
    name: str = Form('api-task'),
    mode: str = Form('rule'),
    format: str = Form('html,csv,xlsx'),
    auto: bool = Form(False),
):
    path = UPLOAD_DIR / file.filename
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(await file.read())
    if auto or not devtype or not brand:
        devtype, brand, scores = identify_file(path)
    else:
        scores = []
    eng = init_db(DEFAULT_DB)
    with Session(eng) as session:
        task, results, reports = run_check(session, path, devtype, brand, name, mode, format)
        return {
            'task_id': task.id,
            'name': task.name,
            'devtype': devtype,
            'brand': brand,
            'identify_scores': scores,
            'result_count': len(results),
            'reports': [str(p) for p in reports],
        }


@app.get('/tasks')
def list_tasks(limit: int = 50):
    eng = init_db(DEFAULT_DB)
    with Session(eng) as session:
        tasks = session.exec(select(CheckTask).order_by(CheckTask.id.desc()).limit(limit)).all()
        return [t.model_dump() for t in tasks]


@app.get('/tasks/{task_id}')
def get_task(task_id: int):
    eng = init_db(DEFAULT_DB)
    with Session(eng) as session:
        task = session.get(CheckTask, task_id)
        if not task:
            raise HTTPException(status_code=404, detail='task not found')
        return task.model_dump()


@app.get('/tasks/{task_id}/download')
def download_report(task_id: int, index: int = 0):
    eng = init_db(DEFAULT_DB)
    with Session(eng) as session:
        task = session.get(CheckTask, task_id)
        if not task or not task.report_path:
            raise HTTPException(status_code=404, detail='report not found')
        paths = [Path(p) for p in task.report_path.split(';') if p]
        if index < 0 or index >= len(paths):
            raise HTTPException(status_code=404, detail='report index not found')
        path = paths[index]
        if not path.exists():
            raise HTTPException(status_code=404, detail='report file missing')
        return FileResponse(path, filename=path.name)
