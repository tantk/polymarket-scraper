@echo off
setlocal

cd /d "%~dp0"

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt >nul 2>&1
playwright install chromium >nul 2>&1

echo Running PnL Extractor (Batch Mode)... >> console_debug.txt
python extract_react_pnl.py --input-file users_list.txt %* >> console_debug.txt 2>&1

echo Done. >> console_debug.txt
exit 0
