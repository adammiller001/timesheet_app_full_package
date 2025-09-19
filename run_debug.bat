@echo on
setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "APP_FILE=app\app.py"

if not exist "%APP_FILE%" (
  echo [ERROR] Missing %APP_FILE%
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv 2>nul || python -m venv .venv
)
call ".venv\Scripts\activate.bat"

python -m pip install --upgrade pip
if exist "requirements.txt" (
  pip install -r requirements.txt
) else (
  pip install streamlit pandas openpyxl xlsxwriter
)

set "PORT=8501"
streamlit run "%APP_FILE%" --server.port=%PORT% --server.headless=false

echo.
pause
