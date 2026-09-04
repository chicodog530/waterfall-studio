#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  echo "Waterfall Studio is not installed. Running installer.sh..."
  ./installer.sh
fi
exec .venv/bin/python waterfall_studio.py
