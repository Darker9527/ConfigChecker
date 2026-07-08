@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
setlocal
cd /d "%~dp0"
python -m configchecker init-db
python -m configchecker import-baseline examples\baseline_seed.csv
python -m configchecker summary
pause
