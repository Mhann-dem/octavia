@echo off
cd /d "%~dp0"
python -m uvicorn app.main:app --reload --port 8001
