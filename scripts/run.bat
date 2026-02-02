@echo off
cd /d "%~dp0.."
echo Starting Commodity Volatility Strategies...

:: Ensure temp directory exists
if not exist "temp" mkdir "temp"

:: Determine Python executable
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    echo [Launcher] Using virtual environment Python: .venv\Scripts\python.exe
) else (
    set "PYTHON_EXE=python"
    echo [Launcher] Virtual environment not found. Using system Python.
)

:: Loop through all timeframe configurations
for %%f in (config\timeframe\*.yaml) do (
    echo [Launcher] Starting process for: %%~nf
    start "Strategy_%%~nf" cmd /k %PYTHON_EXE% src\main\main.py --mode daemon --config config\strategy_config.yaml --override-config "%%f"
    
    :: Wait a bit between starts to prevent CPU spikes
    timeout /t 2 /nobreak >nul
)

echo.
echo All strategies have been launched.
echo Check the new windows for status.
echo.
pause
