@echo off
REM One-time setup: creates .venv and installs the app with the native-window extra.
cd /d "%~dp0"
set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY (where python >nul 2>nul && set PY=python)
if not defined PY goto :nopython
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" || goto :oldpython
%PY% -m venv .venv || goto :err
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -e .[native,dev] || goto :err
echo.
echo Setup complete. Start the app with run.bat
pause
exit /b 0
:nopython
echo Python not found. Install Python 3.12+ from python.org with "Add python.exe to PATH" checked, then rerun.
pause
exit /b 1
:oldpython
echo Python 3.12 or newer is required. Install it from python.org, then rerun.
pause
exit /b 1
:err
echo Setup failed. Copy the messages above and send them over.
pause
exit /b 1
