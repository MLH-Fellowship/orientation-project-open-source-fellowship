"""Token usage: recorded on the assistant message, summed by the usage endpoint."""

from unittest.mock import Mock

from conftest import TestingSessionLocal
from fastapi.testclient import TestClient

from app.llm.base import LLMReply
from app.main import app
from app.models import Message
from app.routes import chat

client = TestClient(app)


def _mock_provider(monkeypatch, *replies):
    provider = Mock()
    provider.generate_reply.side_effect = list(replies)
    monkeypatch.setattr(chat, "get_llm_provider", lambda: provider)
    return provider


def _send(conversation_id, content="hi"):
    return client.post(
        f"/api/conversations/{conversation_id}/messages", json={"content": content}
    )


def test_usage_is_saved_on_the_assistant_message(monkeypatch):
    _mock_provider(
        monkeypatch, LLMReply(text="Paris.", prompt_tokens=12, completion_tokens=3)
    )
    convo = client.post("/api/conversations", json={}).json()

    reply = _send(convo["id"])

    assert reply.status_code == 200
    db = TestingSessionLocal()
    try:
        saved = db.get(Message, reply.json()["id"])
        assert (saved.prompt_tokens, saved.completion_tokens) == (12, 3)
        user_msg = db.query(Message).filter_by(role="user").one()
        assert (user_msg.prompt_tokens, user_msg.completion_tokens) == (None, None)
    finally:
        db.close()


def test_usage_endpoint_sums_over_the_conversation(monkeypatch):
    _mock_provider(
        monkeypatch,
        LLMReply(text="one", prompt_tokens=10, completion_tokens=4),
        LLMReply(text="two", prompt_tokens=20, completion_tokens=6),
    )
    convo = client.post("/api/conversations", json={}).json()
    _send(convo["id"])
    _send(convo["id"])

    response = client.get(f"/api/conversations/{convo['id']}/usage")

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": convo["id"],
        "prompt_tokens": 30,
        "completion_tokens": 10,
        "total_tokens": 40,
        "messages_with_usage": 2,
    }


def test_usage_endpoint_is_zero_for_a_conversation_with_no_replies():
    convo = client.post("/api/conversations", json={}).json()

    body = client.get(f"/api/conversations/{convo['id']}/usage").json()

    assert body["prompt_tokens"] == 0
    assert body["completion_tokens"] == 0
    assert body["total_tokens"] == 0
    assert body["messages_with_usage"] == 0


def test_usage_endpoint_skips_replies_without_counts(monkeypatch):
    """A provider that reports no usage must not break the totals."""
    _mock_provider(
        monkeypatch,
        LLMReply(text="counted", prompt_tokens=7, completion_tokens=2),
        LLMReply(text="uncounted"),
    )
    convo = client.post("/api/conversations", json={}).json()
    _send(convo["id"])
    _send(convo["id"])

    body = client.get(f"/api/conversations/{convo['id']}/usage").json()

    assert body["total_tokens"] == 9
    assert body["messages_with_usage"] == 1


def test_usage_endpoint_only_counts_its_own_conversation(monkeypatch):
    _mock_provider(
        monkeypatch,
        LLMReply(text="mine", prompt_tokens=5, completion_tokens=1),
        LLMReply(text="theirs", prompt_tokens=100, completion_tokens=100),
    )
    first = client.post("/api/conversations", json={}).json()
    second = client.post("/api/conversations", json={}).json()
    _send(first["id"])
    _send(second["id"])

    body = client.get(f"/api/conversations/{first['id']}/usage").json()

    assert body["total_tokens"] == 6


def test_usage_endpoint_not_found():
    assert client.get("/api/conversations/does-not-exist/usage").status_code == 404
