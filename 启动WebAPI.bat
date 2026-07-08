@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
setlocal
cd /d "%~dp0"
uvicorn configchecker.api:app --host 0.0.0.0 --port 8000
pause
