@echo off
REM One-time setup: creates .venv with Python 3.13 or 3.12 and installs the app.
REM Newer Pythons (3.14+) lack prebuilt packages for some dependencies and fail to install.
cd /d "%~dp0"
set PY=
py -3.13 -c "pass" >nul 2>nul && set PY=py -3.13
if not defined PY (py -3.12 -c "pass" >nul 2>nul && set PY=py -3.12)
if not defined PY goto :nopython
echo Using %PY%
if exist .venv rmdir /s /q .venv
%PY% -m venv .venv || goto :err
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install --prefer-binary -e .[native,dev] || goto :err
echo.
echo Setup complete. Start the app with run.bat
pause
exit /b 0
:nopython
echo Python 3.13 (or 3.12) not found. Install Python 3.13 from python.org
echo (Windows installer 64-bit), then rerun setup.bat. Other Python versions can stay installed.
pause
exit /b 1
:err
echo Setup failed. Copy the messages above and send them over.
pause
exit /b 1
