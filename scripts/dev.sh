#!/usr/bin/env bash
# Runs backend (FastAPI/uvicorn) and frontend (Vite) together for local dev.
# Requires: backend venv set up + deps installed, frontend `npm install` run.
set -e

trap 'kill 0' EXIT

(cd backend && uvicorn app.main:app --reload --port 8000) &
(cd frontend && npm run dev) &

wait
