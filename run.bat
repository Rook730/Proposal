@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo .venv not found. Run setup.bat first, from this same folder.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m proposal_builder %*
if errorlevel 1 pause
