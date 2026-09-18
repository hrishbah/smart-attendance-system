#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/backend"

# Do not use backend/deps — packages must come from the venv site-packages
unset PYTHONPATH

VENV_PYTHON="${PWD}/venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv venv
  "$VENV_PYTHON" -m pip install --upgrade pip
  "$VENV_PYTHON" -m pip install -r requirements.txt
fi

if [ ! -f ".env" ]; then
  cp ../.env.example .env
fi

echo "Starting backend on http://localhost:8000"
exec "$VENV_PYTHON" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
