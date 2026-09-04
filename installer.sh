#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.11 or newer is required." >&2
  exit 1
fi

echo "Creating Waterfall Studio virtual environment..."
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' || {
  echo "Python 3.11 or newer is required." >&2
  exit 1
}
python -m pip install --upgrade setuptools wheel
python -m pip install -e .
python -c 'import PySide6, numpy, PIL, sounddevice, serial, ui'

echo
echo "Python environment and dependencies verified successfully."
if command -v rigctld >/dev/null 2>&1; then
  echo "Optional Hamlib rigctld detected."
else
  echo "Optional Hamlib rigctld was not found. Other PTT methods will still work."
fi
echo "Installation complete. Run ./run_linux.sh to start Waterfall Studio."
