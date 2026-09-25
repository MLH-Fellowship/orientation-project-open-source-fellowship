"""
Minimal data model for a chat application.

Conversation  -> has many Messages
Message       -> belongs to a Conversation, has a role (user/assistant)

This is intentionally bare. Fellows will extend it with a User model,
timestamps/soft-deletes, token usage tracking, etc. (see ISSUES.md).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    event,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


DEFAULT_TITLE = "New Conversation"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    hashed_password = Column(String, nullable=True)

    conversations = relationship("Conversation", back_populates="user")  # no cascade


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=_uuid)
    title = Column(String, default=DEFAULT_TITLE)
    # True until a title is auto-generated or the user renames the
    # conversation, whichever happens first. Addresses an edge case where a user
    # renames a conversation to the default title.
    title_is_default = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="conversations")

    # Cascade is enforced by the ORM, not by SQLite: deleting a Conversation
    # through a session deletes its messages, but a bulk query.delete() or raw
    # SQL leaves them orphaned. See "Cascade deletes" in the README.
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )


@event.listens_for(Conversation, "before_insert")
def set_title_is_default(mapper, connection, target):
    target.title_is_default = target.title == DEFAULT_TITLE


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
