@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
setlocal
cd /d "%~dp0"
python -m configchecker migrate-original ..\ConfigChecker_v2.0.0\ConfigChecker_v2.0.0\data.db
python -m configchecker summary
pause
