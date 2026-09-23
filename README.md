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
  alembic/             # database migration scripts
  alembic.ini           # alembic configuration
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

macOS/Linux:

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your Gemini_API_Key
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Windows (Git Bash), venv only creates a `Scripts/` directory, not `bin/`:

```bash
cd backend
py -3.12 -m venv .venv && source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env   # then add your Gemini_API_Key
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

The server picks up `GEMINI_API_KEY` once at startup, and `--reload` only
watches `.py` files, not `.env`. If you edit `.env` while the server is
running, restart it to pick up the change.

Optionally, seed a couple of sample conversations so the frontend has
something to show without needing a live LLM key:

```bash
python scripts/seed.py
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

This uses [`concurrently`](https://www.npmjs.com/package/concurrently) (a
frontend dev dependency, so run `npm install` in `frontend/` first). Output
from each process is labeled `[backend]` or `[frontend]`, and a single
Ctrl+C stops both.

### Or use the Makefile

```bash
make backend-install
make frontend-install
make dev
```

`make backend-install` creates the backend venv, installs dependencies, and
copies `.env.example` to `.env` if it doesn't already exist. Other targets:
`make backend-run`, `make frontend-run`.

The Makefile needs a POSIX shell (`test`, `cp`) and `make` itself, so on
Windows run it from Git Bash or WSL, not plain `cmd.exe` or PowerShell.

### Or use Docker

Runs both containers, no local Python or Node needed:

```bash
cp backend/.env.example backend/.env   # then add your Gemini API key
docker compose up --build
```

Then visit `http://localhost:5173`. The Vite dev server proxies `/api` to the
backend container, and both containers mount your working copy, so edits
reload the same way they do locally.

Stop with `Ctrl-C`, or `docker compose down` to remove the containers.

Notes:

- The backend reads `backend/.env`, the same file the local setup uses. It is
  optional -- compose starts without it, but LLM calls need `GEMINI_API_KEY`.
- `app.db` is written to `backend/` on your machine, so conversations survive
  a container restart and are shared with a local (non-Docker) run.
- Outside Docker the proxy still points at `http://localhost:8000`. Compose
  overrides it with `BACKEND_ORIGIN=http://backend:8000`, because inside a
  container `localhost` is that container itself.


## Configuration

### System prompt

The system prompt is a set of instructions sent to the LLM with every
request. It shapes the assistant's tone and behaviour. It applies to every
conversation and is not stored in the database or shown in the chat.

To change it, set `SYSTEM_PROMPT` in `backend/.env`:

```bash
SYSTEM_PROMPT=You are a concise assistant. Answer in two sentences or fewer.
```

If `SYSTEM_PROMPT` is not set, it defaults to `You are a helpful assistant.`
(see `backend/app/config.py`). Restart the backend after changing it.

## Database migrations

Tables are managed with [Alembic](https://alembic.sqlalchemy.org/) instead
of being created automatically on startup. Run migrations after cloning
and any time you pull changes that touch `app/models.py`.

Apply all pending migrations:

```bash
alembic upgrade head
```

### Adding or changing a model

If you add a new model to `app/models.py`, import it in
`backend/alembic/env.py` alongside the existing models:

```python
from app.models import Conversation, Message  # add new models here
```

Alembic's autogenerate only detects models that are actually imported and
registered on `Base.metadata`. If you skip this step, `alembic revision
--autogenerate` will silently generate an empty migration with nothing in
it, since it won't know the new model exists.

Then generate a migration for the change and review the generated file
before committing it, autogenerate is a good starting point but isn't
always exactly right:

```bash
alembic revision --autogenerate -m "describe your change"
```

If you need to roll back the most recent migration:

```bash
alembic downgrade -1
```

### If you already have a local `app.db` from before this change

Older versions of this project created tables automatically on startup.
If your local `app.db` predates Alembic, it has tables but no migration
history, so `alembic upgrade head` will fail because the tables already
exist. Either:

- Keep your existing data and mark it as up to date (safe if your schema
  already matches `app/models.py`, which it will unless you've made local
  edits outside of git):
```bash
  alembic stamp head
```
- Or delete it and let Alembic recreate it from scratch (loses local data,
  but guarantees a clean slate):
```bash
  rm app.db
  alembic upgrade head
```

## Data model

### Indexes

`messages.conversation_id` is indexed. Every message lookup filters on it --
loading a conversation's history, building the prompt for a reply, cascading
a delete -- and SQLite does not index foreign keys automatically, so without
it those queries scan the whole table.

### Cascade deletes

Deleting a conversation deletes its messages, but that rule lives in the ORM
(`cascade="all, delete-orphan"` on `Conversation.messages`), not in the
database. SQLAlchemy loads the child rows and deletes them itself.

What that means in practice:

| How you delete | Messages |
| --- | --- |
| `DELETE /api/conversations/{id}` (what the app does) | deleted |
| `session.delete(conversation)` | deleted |
| `session.query(Conversation).filter(...).delete()` | orphaned |
| raw `DELETE FROM conversations ...` | orphaned |

The last two bypass the ORM, so nothing cleans up the messages. They are not
rejected either: SQLite only enforces foreign keys when `PRAGMA
foreign_keys=ON` is set per connection, and this project does not set it.

So: delete conversations through a session, which is what every current code
path does. Enforcing this in the database instead would mean adding
`ondelete="CASCADE"` to the foreign key, enabling the pragma on connect, and
shipping a migration -- worth doing if bulk deletes are ever added.

## API

With the backend running, interactive API docs (Swagger UI) are at
`http://localhost:8000/docs`, and the raw OpenAPI schema is at
`http://localhost:8000/openapi.json`.

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
