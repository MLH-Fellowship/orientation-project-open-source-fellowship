"""
Core conversation + messaging endpoints.

This is the minimum needed for the UI to create a conversation, send a
message, and get an LLM reply back. Pagination, streaming, rename,
delete, etc. are left as fellow issues -- see ISSUES.md.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.llm import get_llm_provider
from app.models import Conversation, Message
from app.schemas import (
    ConversationCreate,
    ConversationDetailOut,
    ConversationListOut,
    ConversationOut,
    ConversationUpdate,
    MessageCreate,
    MessageOut,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])
db_dependency = Depends(get_db)


@router.post("", response_model=ConversationOut)
def create_conversation(payload: ConversationCreate, db: Session = db_dependency):
    convo = Conversation(title=payload.title or "New Conversation")
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


@router.get("", response_model=ConversationListOut)
def list_conversations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = db_dependency,
):
    query = db.query(Conversation).order_by(Conversation.created_at.desc())
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return ConversationListOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(conversation_id: str, db: Session = db_dependency):
    convo = db.get(Conversation, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return convo


@router.patch("/{conversation_id}", response_model=ConversationOut)
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


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, db: Session = db_dependency):
    convo = db.get(Conversation, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.delete(convo)
    db.commit()


@router.post("/{conversation_id}/messages", response_model=MessageOut)
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
    reply_text = llm.generate_reply(history)

    assistant_msg = Message(
        conversation_id=conversation_id, role="assistant", content=reply_text
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg
