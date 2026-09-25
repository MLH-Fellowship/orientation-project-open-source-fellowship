"""Schema-level guards for the indexes and cascade rules documented in the README."""

from alembic.config import Config
from alembic.script import ScriptDirectory
from conftest import BACKEND_DIR, TestingSessionLocal
from sqlalchemy import text

from app.models import Conversation, Message


def _head_revision() -> str:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return ScriptDirectory.from_config(config).get_current_head()


def test_conversation_id_is_indexed():
    """Without this index, every message lookup scans the messages table."""
    indexed = {tuple(index.columns.keys()) for index in Message.__table__.indexes}
    assert ("conversation_id",) in indexed


def test_migrations_built_the_test_schema():
    """The fixture runs `alembic upgrade head`, so the suite tests real DDL."""
    db = TestingSessionLocal()
    try:
        stamped = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    finally:
        db.close()
    assert stamped == _head_revision()


def test_index_was_created_by_the_migration():
    """Reads the migrated schema, not the model -- see issue 72."""
    db = TestingSessionLocal()
    try:
        names = [row[1] for row in db.execute(text("PRAGMA index_list(messages)"))]
    finally:
        db.close()
    assert "ix_messages_conversation_id" in names


def test_session_delete_cascades_to_messages():
    """The ORM cascade the app relies on -- see "Cascade deletes" in the README."""
    db = TestingSessionLocal()
    try:
        convo = Conversation(title="cascade")
        db.add(convo)
        db.flush()
        db.add(Message(conversation_id=convo.id, role="user", content="hi"))
        db.commit()

        db.delete(db.get(Conversation, convo.id))
        db.commit()

        assert db.query(Message).filter_by(conversation_id=convo.id).count() == 0
    finally:
        db.close()
