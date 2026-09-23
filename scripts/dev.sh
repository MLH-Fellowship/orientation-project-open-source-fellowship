#!/usr/bin/env bash
set -e

if [ -x "backend/.venv/bin/uvicorn" ]; then
  UVICORN="backend/.venv/bin/uvicorn"
elif [ -x "backend/.venv/Scripts/uvicorn.exe" ]; then
  UVICORN="backend\.venv\Scripts\uvicorn"
else
  echo "Backend virtualenv not found at backend/.venv. Create it and install requirements first (see the README backend setup)." >&2
  exit 1
fi

CONCURRENTLY="frontend/node_modules/.bin/concurrently"

if [ ! -x "$CONCURRENTLY" ]; then
  echo "concurrently is not installed. Run 'npm install' in frontend/ first." >&2
  exit 1
fi

exec "$CONCURRENTLY" \
  --kill-others \
  --names backend,frontend \
  --prefix-colors blue,green \
  "$UVICORN app.main:app --reload --reload-dir backend --port 8000 --app-dir backend" \
  "npm --prefix frontend run dev"
