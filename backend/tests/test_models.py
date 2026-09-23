"""Schema-level guards for the indexes and cascade rules documented in the README."""

from conftest import TestingSessionLocal
from sqlalchemy import text

from app.models import Conversation, Message


def test_conversation_id_is_indexed():
    """Without this index, every message lookup scans the messages table."""
    indexed = {tuple(index.columns.keys()) for index in Message.__table__.indexes}
    assert ("conversation_id",) in indexed


def test_index_exists_in_the_database():
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
