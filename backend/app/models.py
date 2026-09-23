"""
Minimal data model for a chat application.

Conversation  -> has many Messages
Message       -> belongs to a Conversation, has a role (user/assistant)

This is intentionally bare. Fellows will extend it with a User model,
timestamps/soft-deletes, token usage tracking, etc. (see ISSUES.md).
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=_uuid)
    title = Column(String, default="New Conversation")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Cascade is enforced by the ORM, not by SQLite: deleting a Conversation
    # through a session deletes its messages, but a bulk query.delete() or raw
    # SQL leaves them orphaned. See "Cascade deletes" in the README.
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=_uuid)
    # Indexed: every message lookup filters on this column (loading a
    # conversation's history, cascading a delete), and SQLite does not
    # index foreign keys on its own.
    conversation_id = Column(
        String, ForeignKey("conversations.id"), nullable=False, index=True
    )
    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Token usage for this reply, as reported by the provider. Null on user
    # messages, on streamed replies (issue 64), and when the provider does
    # not report usage.
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")
