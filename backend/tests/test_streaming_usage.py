"""Token usage for streamed replies (issue 64).

Usage only arrives in the provider's final chunk, after the text has been
sent, so the provider records it and the route reads it once the stream ends.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest
from conftest import TestingSessionLocal
from fastapi.testclient import TestClient

from app.llm.base import TokenUsage
from app.llm.gemini_provider import GeminiProvider
from app.main import app
from app.models import Message
from app.routes import chat

client = TestClient(app)


class _StreamingProvider:
    """Reports usage at the end of the stream, the way Gemini does."""

    def __init__(self, usage=None):
        self._usage = usage
        self.last_usage = None

    async def stream_reply(self, history, system_prompt):
        yield "hello "
        yield "world"
        self.last_usage = self._usage


def _stream(conversation_id, content="hi"):
    return client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": content},
    )


def _saved_reply():
    db = TestingSessionLocal()
    try:
        return db.query(Message).filter_by(role="assistant").one()
    finally:
        db.close()


def test_streamed_reply_records_usage(monkeypatch):
    provider = _StreamingProvider(TokenUsage(prompt_tokens=31, completion_tokens=9))
    monkeypatch.setattr(chat, "get_llm_provider", lambda: provider)
    convo = client.post("/api/conversations", json={}).json()

    response = _stream(convo["id"])

    assert response.status_code == 200
    saved = _saved_reply()
    assert saved.content == "hello world"
    assert (saved.prompt_tokens, saved.completion_tokens) == (31, 9)


def test_streamed_usage_reaches_the_usage_endpoint(monkeypatch):
    provider = _StreamingProvider(TokenUsage(prompt_tokens=31, completion_tokens=9))
    monkeypatch.setattr(chat, "get_llm_provider", lambda: provider)
    convo = client.post("/api/conversations", json={}).json()
    _stream(convo["id"])

    body = client.get(f"/api/conversations/{convo['id']}/usage").json()

    assert body["total_tokens"] == 40
    assert body["messages_with_usage"] == 1


def test_streamed_reply_without_usage_is_saved_with_null_counts(monkeypatch):
    """A provider that reports nothing must not break the stream."""
    monkeypatch.setattr(chat, "get_llm_provider", lambda: _StreamingProvider(None))
    convo = client.post("/api/conversations", json={}).json()

    response = _stream(convo["id"])

    assert response.status_code == 200
    saved = _saved_reply()
    assert (saved.prompt_tokens, saved.completion_tokens) == (None, None)


def test_mocked_provider_without_real_usage_is_ignored(monkeypatch):
    """last_usage that is not a TokenUsage (e.g. a Mock) is not persisted."""

    async def stream_reply(history, system_prompt):
        yield "hi"

    monkeypatch.setattr(
        chat, "get_llm_provider", lambda: Mock(stream_reply=stream_reply)
    )
    convo = client.post("/api/conversations", json={}).json()

    assert _stream(convo["id"]).status_code == 200
    saved = _saved_reply()
    assert (saved.prompt_tokens, saved.completion_tokens) == (None, None)


def _chunk(text, prompt=None, completion=None):
    usage = None
    if prompt is not None or completion is not None:
        usage = SimpleNamespace(
            prompt_token_count=prompt, candidates_token_count=completion
        )
    return SimpleNamespace(text=text, usage_metadata=usage)


def _chunks(*chunks):
    """A generator, so contextlib.closing has a close() to call."""

    def stream():
        yield from chunks

    return stream()


@pytest.mark.asyncio
async def test_gemini_records_usage_from_the_final_chunk():
    provider = GeminiProvider.__new__(GeminiProvider)
    provider.client = MagicMock()
    provider.last_usage = None
    provider.client.models.generate_content_stream.return_value = _chunks(
        _chunk("hel"), _chunk("lo", prompt=18, completion=4)
    )

    text = "".join(
        [
            c
            async for c in provider.stream_reply(
                [{"role": "user", "content": "x"}], "s"
            )
        ]
    )

    assert text == "hello"
    assert provider.last_usage == TokenUsage(prompt_tokens=18, completion_tokens=4)


@pytest.mark.asyncio
async def test_gemini_leaves_usage_unset_when_none_is_reported():
    provider = GeminiProvider.__new__(GeminiProvider)
    provider.client = MagicMock()
    provider.last_usage = None
    provider.client.models.generate_content_stream.return_value = _chunks(_chunk("hi"))

    [c async for c in provider.stream_reply([{"role": "user", "content": "x"}], "s")]

    assert provider.last_usage is None
