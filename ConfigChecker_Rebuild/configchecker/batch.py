# -*- coding: utf-8 -*-
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from sqlmodel import Session
from .db import init_db
from .cli import run_check


def run_batch_parallel(db_path: str, directory: str, devtype: str, brand: str, name: str, mode: str, formats: str, workers: int = 4):
    files = [p for p in Path(directory).iterdir() if p.is_file()]

    def one(path: Path):
        eng = init_db(db_path)
        with Session(eng) as session:
            task_name = f'{name}_{path.stem}'
            _, results, reports = run_check(session, path, devtype, brand, task_name, mode, formats)
            return path.name, len(results), reports

    output = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        future_map = {ex.submit(one, p): p for p in files}
        for fut in as_completed(future_map):
            output.append(fut.result())
    return output
