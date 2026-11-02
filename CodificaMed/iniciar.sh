#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
[ -f .env ] || { echo "Copia .env.example como .env"; exit 1; }
. .venv/bin/activate
PUERTO=$(sed -n 's/^PUERTO=//p' .env | head -1)
PUERTO=${PUERTO:-8001}
python -m uvicorn app.main:app --host 127.0.0.1 --port "$PUERTO"
