@echo off
cd /d "%~dp0.."
set PYTHONPATH=%cd%
call .venv\Scripts\activate.bat
python src\main\process\recorder_process.py --log-level INFO
pause
