#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo ".env not found. Run cp .env.example .env and edit it first." >&2
  exit 1
fi

if [ -f .venv/bin/activate ]; then
  . .venv/bin/activate
fi

python -m src.main
