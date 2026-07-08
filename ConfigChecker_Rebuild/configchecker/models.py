# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class Baseline(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    descr: str
    reference: Optional[str] = None
    content: str
    mtime: str = Field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d'))
    devtype: str = Field(index=True)
    brand: str = Field(index=True)
    chktype: str = '1'
    cmd: Optional[str] = None
    risk: str = '中风险'
    level: str = '二级/三级'


class CheckTask(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    devtype: str
    brand: str
    config_path: str
    asset_id: Optional[int] = Field(default=None, index=True)
    score: Optional[float] = None
    report_path: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


class CheckResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(index=True)
    baseline_id: int = Field(index=True)
    baseline_name: str
    status: str
    risk: str
    evidence: str = ''
    suggestion: str = ''
    reason: str = ''


class SysConfig(SQLModel, table=True):
    config: str = Field(primary_key=True)
    value: str


class Asset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    ip: str = ''
    hostname: str = ''
    devtype: str = Field(index=True)
    brand: str = Field(index=True)
    owner: str = ''
    department: str = ''
    importance: str = '一般'
    tags: str = ''
    created_at: str = Field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    updated_at: str = Field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


class ExceptionItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: Optional[int] = Field(default=None, index=True)
    baseline_id: int = Field(index=True)
    reason: str
    owner: str = ''
    expire_at: str = ''
    approved_by: str = ''
    status: str = '有效'
    created_at: str = Field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
