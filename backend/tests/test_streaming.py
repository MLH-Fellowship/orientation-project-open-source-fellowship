import asyncio
import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.llm.base import LLMReply
from app.main import app
from app.routes import chat

client = TestClient(app)


@pytest.fixture(autouse=True)
def _no_title_generation(monkeypatch):
    """Stub out title generation: it races the reply save on the shared test connection."""
    monkeypatch.setattr(
        chat, "_generate_conversation_title", lambda bind, conversation_id: None
    )


def _events(response):
    events = []
    for block in response.text.strip().split("\n\n"):
        event, data = block.split("\n")
        events.append(
            (event.removeprefix("event: "), json.loads(data.removeprefix("data: ")))
        )
    return events


def test_stream_sends_chunks_and_saves_reply(monkeypatch):
    history = []
    prompts = []
    monkeypatch.setattr(chat.settings, "system_prompt", "Answer like a pirate.")

    async def stream_reply(messages, system_prompt):
        history.extend(messages)
        prompts.append(system_prompt)
        yield 'Hello "friend"\n'
        yield ""
        yield "Goodbye 🌍"

    provider = Mock(stream_reply=stream_reply)
    monkeypatch.setattr(chat, "get_llm_provider", lambda: provider)
    convo = client.post("/api/conversations", json={}).json()
    path = f"/api/conversations/{convo['id']}"
    response = client.post(f"{path}/messages/stream", json={"content": "hello"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    events = _events(response)
    assert events[:2] == [
        ("token", {"content": 'Hello "friend"\n'}),
        ("token", {"content": "Goodbye 🌍"}),
    ]
    assert len(events) == 3
    assert events[2][0] == "done"
    message = events[2][1]
    assert message["role"] == "assistant"
    assert message["content"] == 'Hello "friend"\nGoodbye 🌍'
    assert message["id"]
    assert message["created_at"]
    assert history == [{"role": "user", "content": "hello"}]
    assert prompts == ["Answer like a pirate."]
    messages = client.get(path).json()["messages"]
    assert len(messages) == 2
    assert next(m for m in messages if m["role"] == "assistant") == message

    history.clear()
    client.post(f"{path}/messages/stream", json={"content": "again"})
    assert history == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": message["content"]},
        {"role": "user", "content": "again"},
    ]
    provider.generate_reply.assert_not_called()


@pytest.mark.parametrize("partial", [False, True])
def test_stream_failure_does_not_save_partial_reply(monkeypatch, partial):
    closed = []

    async def stream_reply(history, system_prompt):
        try:
            if partial:
                yield "Partial reply"
            raise RuntimeError("private provider details")
        finally:
            closed.append(True)

    monkeypatch.setattr(
        chat, "get_llm_provider", lambda: Mock(stream_reply=stream_reply)
    )
    convo = client.post("/api/conversations", json={}).json()
    path = f"/api/conversations/{convo['id']}"
    response = client.post(f"{path}/messages/stream", json={"content": "hello"})

    assert response.status_code == 200
    events = _events(response)
    assert [event for event, _ in events] == (
        ["token", "error"] if partial else ["error"]
    )
    assert events[-1][1] == {
        "error": {"code": 500, "message": "Could not generate reply"}
    }
    assert "private provider details" not in response.text
    assert closed == [True]
    messages = client.get(path).json()["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"


def test_empty_stream_returns_error(monkeypatch):
    async def stream_reply(history, system_prompt):
        yield ""

    monkeypatch.setattr(
        chat, "get_llm_provider", lambda: Mock(stream_reply=stream_reply)
    )
    convo = client.post("/api/conversations", json={}).json()
    path = f"/api/conversations/{convo['id']}"
    response = client.post(f"{path}/messages/stream", json={"content": "hello"})

    assert [event for event, _ in _events(response)] == ["error"]
    assert len(client.get(path).json()["messages"]) == 1


def test_stream_provider_setup_failure_returns_error(monkeypatch):
    monkeypatch.setattr(
        chat, "get_llm_provider", Mock(side_effect=ValueError("secret"))
    )
    convo = client.post("/api/conversations", json={}).json()
    response = client.post(
        f"/api/conversations/{convo['id']}/messages/stream", json={"content": "hello"}
    )

    assert [event for event, _ in _events(response)] == ["error"]
    assert "secret" not in response.text


def test_stream_save_failure_returns_error(monkeypatch):
    async def stream_reply(history, system_prompt):
        yield "hello"

    monkeypatch.setattr(
        chat, "get_llm_provider", lambda: Mock(stream_reply=stream_reply)
    )
    monkeypatch.setattr(
        chat, "_save_streamed_reply", Mock(side_effect=RuntimeError("secret"))
    )
    convo = client.post("/api/conversations", json={}).json()
    path = f"/api/conversations/{convo['id']}"
    response = client.post(f"{path}/messages/stream", json={"content": "hello"})

    assert [event for event, _ in _events(response)] == ["token", "error"]
    assert "secret" not in response.text
    assert len(client.get(path).json()["messages"]) == 1


def test_stream_rejects_missing_conversation_and_invalid_payload(monkeypatch):
    provider = Mock()
    monkeypatch.setattr(chat, "get_llm_provider", provider)
    response = client.post(
        "/api/conversations/missing/messages/stream", json={"content": "hi"}
    )
    assert response.status_code == 404

    convo = client.post("/api/conversations", json={}).json()
    response = client.post(f"/api/conversations/{convo['id']}/messages/stream", json={})
    assert response.status_code == 422
    provider.assert_not_called()


def test_original_message_endpoint_still_returns_json(monkeypatch):
    provider = Mock()
    provider.generate_reply.return_value = LLMReply(text="hello")
    provider.generate_conversation_title.return_value = "..."
    monkeypatch.setattr(chat, "get_llm_provider", lambda: provider)
    convo = client.post("/api/conversations", json={}).json()
    response = client.post(
        f"/api/conversations/{convo['id']}/messages", json={"content": "hi"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json()["content"] == "hello"
    provider.stream_reply.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("disconnect", [False, True])
async def test_stream_delivers_before_completion_and_closes_on_disconnect(
    monkeypatch, disconnect
):
    delivered = asyncio.Event()
    closed = asyncio.Event()
    sent = []

    async def stream_reply(history, system_prompt):
        try:
            yield "first"
            await delivered.wait()
            if disconnect:
                await asyncio.Event().wait()
            yield "second"
        finally:
            closed.set()

    monkeypatch.setattr(
        chat, "get_llm_provider", lambda: Mock(stream_reply=stream_reply)
    )
    convo = client.post("/api/conversations", json={}).json()
    path = f"/api/conversations/{convo['id']}"
    request_sent = False

    async def receive():
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {
                "type": "http.request",
                "body": b'{"content":"hi"}',
                "more_body": False,
            }
        await delivered.wait()
        if disconnect:
            return {"type": "http.disconnect"}
        await asyncio.Event().wait()

    async def send(message):
        sent.append(message)
        if b"event: token" in message.get("body", b""):
            delivered.set()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": f"{path}/messages/stream",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "server": ("testserver", 80),
        "client": ("testclient", 123),
        "root_path": "",
    }
    await asyncio.wait_for(app(scope, receive, send), timeout=5)

    assert delivered.is_set()
    assert closed.is_set()
    body = b"".join(message.get("body", b"") for message in sent)
    messages = client.get(path).json()["messages"]
    if disconnect:
        assert b"event: done" not in body
        assert b"event: error" not in body
        assert len(messages) == 1
    else:
        assert b"event: done" in body
        assert len(messages) == 2
        assert (
            next(m for m in messages if m["role"] == "assistant")["content"]
            == "firstsecond"
        )
