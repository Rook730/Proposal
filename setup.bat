@echo off
REM One-time setup: creates .venv and installs the app with the native-window extra.
cd /d "%~dp0"
py -3 -m venv .venv || goto :err
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -e .[native,dev] || goto :err
echo.
echo Setup complete. Start the app with run.bat
pause
exit /b 0
:err
echo Setup failed. Is Python 3.12+ installed (python.org, "Add to PATH" checked)?
pause
exit /b 1
