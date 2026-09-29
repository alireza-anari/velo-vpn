#!/usr/bin/env bash
set -euo pipefail

BACKEND_DIR="${VELO_BACKEND_DIR:-/opt/velo/backend}"
cd "$BACKEND_DIR"

if [[ ! -x .venv/bin/alembic ]]; then
  echo "alembic not installed in $BACKEND_DIR/.venv" >&2
  exit 1
fi

exec .venv/bin/alembic -c alembic.ini upgrade head
