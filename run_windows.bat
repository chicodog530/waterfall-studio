@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python.exe waterfall_studio.py
) else (
  echo Waterfall Studio is not installed. Running installer.bat...
  call installer.bat
  if errorlevel 1 exit /b 1
  .venv\Scripts\python.exe waterfall_studio.py
)
pause
