"""Pydantic request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class MessageCreate(BaseModel):
    content: str = Field(..., max_length=10000)

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("content must not be empty")
        return value


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationUpdate(BaseModel):
    title: str = Field(..., max_length=200)

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("title must not be empty")
        return value


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut] = []


class ConversationListOut(BaseModel):
    items: list[ConversationOut]
    total: int
    limit: int
    offset: int
