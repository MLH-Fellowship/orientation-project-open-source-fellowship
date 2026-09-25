"""Test database setup.

The schema is built by running the migrations, not by `create_all()`, so the
suite exercises the same upgrade path a real deployment takes.
"""

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from alembic import command
from app.database import Base, get_db
from app.main import api

BACKEND_DIR = Path(__file__).resolve().parent.parent

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _migrate() -> None:
    """Upgrade the in-memory database to head, once per test session."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    with engine.begin() as connection:
        # env.py uses this connection instead of building its own engine,
        # which is what keeps the migrations on the in-memory database.
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


api.dependency_overrides[get_db] = _override_get_db
_migrate()


@pytest.fixture(autouse=True)
def reset_database():
    """Empty the tables between tests, leaving the migrated schema in place."""
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
    yield


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    api.state.limiter.reset()
    yield
