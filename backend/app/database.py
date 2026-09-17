"""
Database engine and session management (SQLAlchemy).

Barebones: SQLite file DB locally, Postgres in production. Tables are
created on startup via Base.metadata.create_all(). A real migration
workflow (Alembic) is left as an open issue for fellows -- see ISSUES.md.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


def _normalize(url: str) -> str:
    """Render hands out postgres:// URLs, which SQLAlchemy 2 no longer accepts."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    return url


database_url = _normalize(settings.database_url)

connect_args = {"check_same_thread": False} if "sqlite" in database_url else {}
engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
