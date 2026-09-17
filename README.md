# Orientation Project - Open Source Fellowship

A barebones full-stack LLM chat application, built as a starting point for
MLH fellows to extend.

## Stack

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite. Talks to an LLM through a small pluggable provider interface.
- **Frontend:** JavaScript, React, Vite (Node-based tooling).
- **Communication:** Frontend calls the backend REST API (Vite dev
  server proxies `/api` to `http://localhost:8000`).

## Requirements

- **Python 3.10 - 3.13.** 3.12 is recommended.
  - **3.14 does not work.** `requirements.txt` pins `pydantic==2.9.2`, which
    needs `pydantic-core==2.23.4`. That ships wheels for cp38-cp313 only, so
    pip falls back to building it from source and the build fails:
    `the configured Python interpreter version (3.14) is newer than PyO3's
maximum supported version (3.13)`.
  - **Below 3.10 does not work.** `app/schemas.py` uses `str | None` (PEP 604)
    and there is no `from __future__ import annotations`, so Pydantic
    evaluates the annotation at runtime.
- **Node 22+.** The current frontend toolchain requires a Node 22 runtime. Older 20.x versions may not satisfy newer package requirements.

## Project layout

```
backend/
  app/
    main.py          # FastAPI app + router registration
    config.py         # env-based settings
    database.py        # SQLAlchemy engine/session
    models.py          # Conversation, Message
    schemas.py          # Pydantic request/response models
    llm/                # pluggable LLM provider interface
    routes/             # health + conversation/chat endpoints
  tests/
frontend/
  src/
    App.jsx             # barebones single-conversation chat UI
    components/          # MessageList, MessageInput
    api/client.js         # fetch wrapper for backend API
scripts/dev.sh            # runs backend + frontend together
```

## Getting started

### Backend

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your Gemini_API_Key
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Then visit `http://localhost:5173`.

### Or run both at once

```bash
./scripts/dev.sh
```

## Debugging GitHub Actions locally

If you’re working on CI workflows, it can be very helpful to run them locally before pushing. A good tool for that is [`act`](https://github.com/nektos/act), which lets you execute GitHub Actions workflows on your machine.

```bash
# Example: run the default workflow locally
act
```

This is useful for catching workflow errors, validating job steps, and iterating faster without repeatedly pushing commits to GitHub.

## What's the point?

We want you to learn how to work on Open Source Projects, create PRs and tackling issues.
Your Pod Leader will be the maintainer of this project, closing PRs and managing the repository.
