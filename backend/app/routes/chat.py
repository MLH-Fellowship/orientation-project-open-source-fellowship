"""
Core conversation + messaging endpoints.

This is the minimum needed for the UI to create a conversation, send a
message, and get an LLM reply back. Pagination, streaming, rename,
delete, etc. are left as fellow issues -- see ISSUES.md.
"""

import json
import logging
from contextlib import aclosing

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.errors import stream_error
from app.llm import get_llm_provider
from app.llm.base import TokenUsage
from app.models import Conversation, Message
from app.schemas import (
    ConversationCreate,
    ConversationDetailOut,
    ConversationListOut,
    ConversationOut,
    ConversationUpdate,
    ConversationUsageOut,
    MessageCreate,
    MessageOut,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])
db_dependency = Depends(get_db)

CONVERSATION_NOT_FOUND = {404: {"description": "Conversation not found"}}
logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=ConversationOut,
    summary="Create a conversation",
    description="Creates a new, empty conversation. If no title is given, defaults to 'New Conversation'.",
)
def create_conversation(payload: ConversationCreate, db: Session = db_dependency):
    convo = Conversation(title=payload.title or "New Conversation")
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


@router.get(
    "",
    response_model=ConversationListOut,
    summary="List conversations",
    description="Returns conversations ordered newest-first, with limit/offset pagination and a total count.",
)
def list_conversations(
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of conversations to return."
    ),
    offset: int = Query(0, ge=0, description="Number of conversations to skip."),
    db: Session = db_dependency,
):
    query = db.query(Conversation).order_by(Conversation.created_at.desc())
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return ConversationListOut(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailOut,
    summary="Get a conversation",
    description="Returns a single conversation along with its full message history.",
    responses=CONVERSATION_NOT_FOUND,
)
def get_conversation(conversation_id: str, db: Session = db_dependency):
    convo = db.get(Conversation, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return convo


@router.patch(
    "/{conversation_id}",
    response_model=ConversationOut,
    summary="Rename a conversation",
    description="Updates a conversation's title. The title must be non-blank after stripping whitespace and at most 200 characters.",
    responses=CONVERSATION_NOT_FOUND,
)
def rename_conversation(
    conversation_id: str, payload: ConversationUpdate, db: Session = db_dependency
):
    convo = db.get(Conversation, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    convo.title = payload.title
    db.commit()
    db.refresh(convo)
    return convo


@router.delete(
    "/{conversation_id}",
    status_code=204,
    summary="Delete a conversation",
    description="Deletes a conversation and all of its messages.",
    responses=CONVERSATION_NOT_FOUND,
)
def delete_conversation(conversation_id: str, db: Session = db_dependency):
    convo = db.get(Conversation, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.delete(convo)
    db.commit()


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageOut,
    summary="Send a message",
    description="Adds a user message to the conversation, gets a reply from the configured LLM provider, and returns the assistant's message.",
    responses=CONVERSATION_NOT_FOUND,
)
def send_message(
    conversation_id: str, payload: MessageCreate, db: Session = db_dependency
):
    convo = db.get(Conversation, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_msg = Message(
        conversation_id=conversation_id, role="user", content=payload.content
    )
    db.add(user_msg)
    db.commit()

    history = [{"role": m.role, "content": m.content} for m in convo.messages]

    llm = get_llm_provider()
    reply = llm.generate_reply(history, settings.system_prompt)

    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=reply.text,
        prompt_tokens=reply.prompt_tokens,
        completion_tokens=reply.completion_tokens,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg


@router.get(
    "/{conversation_id}/usage",
    response_model=ConversationUsageOut,
    summary="Get token usage for a conversation",
    description="Totals the token counts recorded on this conversation's assistant messages.",
    responses=CONVERSATION_NOT_FOUND,
)
def get_conversation_usage(conversation_id: str, db: Session = db_dependency):
    if db.get(Conversation, conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    prompt_tokens, completion_tokens, messages_with_usage = (
        db.query(
            func.coalesce(func.sum(Message.prompt_tokens), 0),
            func.coalesce(func.sum(Message.completion_tokens), 0),
            func.count(Message.id),
        )
        .filter(
            Message.conversation_id == conversation_id,
            Message.prompt_tokens.isnot(None) | Message.completion_tokens.isnot(None),
        )
        .one()
    )

    return ConversationUsageOut(
        conversation_id=conversation_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        messages_with_usage=messages_with_usage,
    )


def _stream_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _save_streamed_reply(
    bind, conversation_id: str, content: str, usage: TokenUsage | None
) -> dict:
    with Session(bind=bind) as db:
        if db.get(Conversation, conversation_id) is None:
            raise ValueError("Conversation no longer exists")
        message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return MessageOut.model_validate(message).model_dump(mode="json")


@router.post(
    "/{conversation_id}/messages/stream",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
def stream_message(
    conversation_id: str, payload: MessageCreate, db: Session = db_dependency
):
    convo = db.get(Conversation, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_msg = Message(
        conversation_id=conversation_id, role="user", content=payload.content
    )
    db.add(user_msg)
    db.commit()
    history = [
        {"role": m.role, "content": m.content}
        for m in sorted(convo.messages, key=lambda m: m.created_at)
    ]
    bind = db.get_bind()

    async def events():
        try:
            llm = get_llm_provider()
            chunks = []
            async with aclosing(
                llm.stream_reply(history, settings.system_prompt)
            ) as stream:
                async for chunk in stream:
                    if chunk:
                        chunks.append(chunk)
                        yield _stream_event("token", {"content": chunk})
            if not chunks:
                raise ValueError("The provider returned no text")
            # The provider records usage once the stream is exhausted; a
            # provider that reports none leaves the columns null.
            usage = getattr(llm, "last_usage", None)
            message = await run_in_threadpool(
                _save_streamed_reply,
                bind,
                conversation_id,
                "".join(chunks),
                usage if isinstance(usage, TokenUsage) else None,
            )
        except Exception as exc:
            logger.exception(
                "Failed to stream reply for conversation %s", conversation_id
            )
            yield _stream_event("error", {"error": stream_error(exc)})
            return
        yield _stream_event("done", message)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
