@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.11 or newer from python.org
  echo and enable "Add Python to PATH", then run this installer again.
  pause
  exit /b 1
)

echo Creating Waterfall Studio virtual environment...
py -3 -m venv .venv || goto :failed
call .venv\Scripts\activate.bat || goto :failed
python -m pip install --upgrade pip || goto :failed
python -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" || (
  echo Python 3.11 or newer is required.
  goto :failed
)
python -m pip install --upgrade setuptools wheel || goto :failed
python -m pip install -e . || goto :failed
python -c "import PySide6, numpy, PIL, sounddevice, serial, ui" || goto :failed

echo.
echo Python environment and dependencies verified successfully.
where rigctld >nul 2>nul
if errorlevel 1 (
  echo Optional Hamlib rigctld was not found. Other PTT methods will still work.
) else (
  echo Optional Hamlib rigctld detected.
)
echo Installation complete. Use run_windows.bat to start Waterfall Studio.
pause
exit /b 0

:failed
echo.
echo Installation failed. Review the error above.
pause
exit /b 1
