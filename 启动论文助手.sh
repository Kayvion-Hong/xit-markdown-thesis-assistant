#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/markdown"
PYTHON=python3
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON=python
"$PYTHON" -c 'import yaml' >/dev/null 2>&1 || "$PYTHON" -m pip install -r requirements.txt
exec "$PYTHON" assistant/app.py
