@echo off
cd /d "%~dp0.."
echo Starting Commodity Volatility Strategy (Paper Trading Mode)...

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
    echo [Launcher] Starting PAPER TRADING process for: %%~nf
    
    :: Use standalone mode for paper trading to ensure the --paper flag is respected
    start "Commodity_volatility_Paper_%%~nf" %PYTHON_EXE% src\main\main.py --mode standalone --config config\strategy_config.yaml --override-config "%%f" --paper
    
    :: Wait a bit between starts to prevent CPU spikes
    timeout /t 2 /nobreak >nul
)

echo.
echo All paper trading strategies have been launched.
echo Check the new windows for status.
echo.
pause
