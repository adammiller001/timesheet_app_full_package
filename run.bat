@echo off
setlocal ENABLEDELAYEDEXPANSION

REM ===== Daily Timesheet App launcher (Windows) =====
REM - Creates/uses .venv in the app folder
REM - Installs deps (requirements.txt if present, otherwise minimal set)
REM - Launches Streamlit app/app.py
REM ===================================================

cd /d "%~dp0"
set "PYTHONUTF8=1"
set "APP_FILE=app\app.py"

if not exist "%APP_FILE%" (
  echo [ERROR] Could not find %APP_FILE% next to this script.
  echo        Make sure you extracted the zip and kept the folder structure.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Creating virtual environment...
  py -3 -m venv .venv 2>nul || python -m venv .venv
)

echo [INFO] Activating virtual environment...
call ".venv\Scripts\activate.bat"

echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

if exist "requirements.txt" (
  echo [INFO] Installing from requirements.txt...
  pip install -r requirements.txt
) else (
  echo [INFO] Installing minimal dependencies...
  pip install streamlit pandas openpyxl xlsxwriter
)

echo [INFO] Starting Streamlit...
streamlit run "%APP_FILE%" --server.headless=false

echo.
echo [DONE] Close this window or press any key to exit.
pause >nul
