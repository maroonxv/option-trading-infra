@echo off
cd /d "%~dp0.."
set PYTHONPATH=%cd%
call .venv\Scripts\activate.bat
python src\main\run_recorder.py --log-level INFO
pause
