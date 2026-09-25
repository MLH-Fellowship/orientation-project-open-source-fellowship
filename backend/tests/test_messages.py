from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, settings
from app.llm.base import LLMReply
from app.main import app
from app.routes import chat

client = TestClient(app)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"content": None},
        {"content": 123},
        {"content": []},
        {"content": {}},
        {"content": ""},
        {"content": " \t\n "},
        {"content": "x" * 10001},
    ],
)
def test_send_message_rejects_invalid_content(payload, monkeypatch):
    provider = Mock()
    monkeypatch.setattr(chat, "get_llm_provider", provider)
    convo = client.post("/api/conversations", json={}).json()

    response = client.post(f"/api/conversations/{convo['id']}/messages", json=payload)

    assert response.status_code == 422
    provider.assert_not_called()
    fetched = client.get(f"/api/conversations/{convo['id']}")
    assert fetched.json()["messages"] == []


@pytest.mark.parametrize(
    "content, expected",
    [
        ("x", "x"),
        (" \tHello\nworld! \n", "Hello\nworld!"),
        ("x" * 10000, "x" * 10000),
        ("  " + "x" * 10000 + "  ", "x" * 10000),
    ],
)
def test_send_message_accepts_and_trims_valid_content(content, expected, monkeypatch):
    provider = Mock()
    provider.generate_reply.return_value = LLMReply(text="Hello back")
    provider.generate_conversation_title.return_value = "Greeting"
    monkeypatch.setattr(chat, "get_llm_provider", lambda: provider)

    convo = client.post("/api/conversations", json={}).json()

    response = client.post(
        f"/api/conversations/{convo['id']}/messages", json={"content": content}
    )

    assert response.status_code == 200
    assert response.json()["content"] == "Hello back"
    provider.generate_reply.assert_called_once_with(
        [{"role": "user", "content": expected}], settings.system_prompt
    )

    fetched = client.get(f"/api/conversations/{convo['id']}")
    convo = fetched.json()

    assert convo["title"] == "Greeting"

    user_messages = [m for m in convo["messages"] if m["role"] == "user"]
    assert len(user_messages) == 1
    assert user_messages[0]["content"] == expected


def test_send_message_passes_configured_system_prompt(monkeypatch):
    """The configured system prompt reaches the provider on every call."""
    monkeypatch.setattr(settings, "system_prompt", "Always reply in pirate speak.")
    provider = Mock()
    provider.generate_reply.return_value = LLMReply(text="Arrr")
    provider.generate_conversation_title.return_value = "..."
    monkeypatch.setattr(chat, "get_llm_provider", lambda: provider)
    convo = client.post("/api/conversations", json={}).json()

    response = client.post(
        f"/api/conversations/{convo['id']}/messages", json={"content": "hi"}
    )

    assert response.status_code == 200
    history, system_prompt = provider.generate_reply.call_args.args
    assert history == [{"role": "user", "content": "hi"}]
    assert system_prompt == "Always reply in pirate speak."


def test_system_prompt_falls_back_to_default():
    """With no SYSTEM_PROMPT in the environment, the default is used."""
    assert Settings(_env_file=None).system_prompt == "You are a helpful assistant."


def test_send_message_persists_user_and_assistant_messages(monkeypatch):
    provider = Mock()
    provider.generate_reply.return_value = LLMReply(text="Paris.")
    provider.generate_conversation_title.return_value = "..."
    monkeypatch.setattr(chat, "get_llm_provider", lambda: provider)
    convo = client.post("/api/conversations", json={}).json()

    response = client.post(
        f"/api/conversations/{convo['id']}/messages",
        json={"content": "Capital of France?"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "assistant"
    messages = client.get(f"/api/conversations/{convo['id']}").json()["messages"]
    assert [(m["role"], m["content"]) for m in messages] == [
        ("user", "Capital of France?"),
        ("assistant", "Paris."),
    ]


def test_send_message_sends_prior_history_to_the_provider(monkeypatch):
    """A follow-up message carries the earlier turns with it."""
    provider = Mock()
    provider.generate_reply.side_effect = [
        LLMReply(text="Paris."),
        LLMReply(text="About 2.1 million."),
    ]
    provider.generate_conversation_title.return_value = "..."
    monkeypatch.setattr(chat, "get_llm_provider", lambda: provider)
    convo = client.post("/api/conversations", json={}).json()

    client.post(
        f"/api/conversations/{convo['id']}/messages",
        json={"content": "Capital of France?"},
    )
    client.post(
        f"/api/conversations/{convo['id']}/messages",
        json={"content": "Population?"},
    )

    history, _ = provider.generate_reply.call_args.args
    assert history == [
        {"role": "user", "content": "Capital of France?"},
        {"role": "assistant", "content": "Paris."},
        {"role": "user", "content": "Population?"},
    ]


def test_send_message_does_not_regenerate_title_once_set(monkeypatch):
    """Once a real title has been generated, later messages leave it alone."""
    provider = Mock()
    provider.generate_reply.side_effect = [
        LLMReply(text="Paris."),
        LLMReply(text="About 2.1 million."),
    ]
    provider.generate_conversation_title.return_value = "Capital of France"
    monkeypatch.setattr(chat, "get_llm_provider", lambda: provider)
    convo = client.post("/api/conversations", json={}).json()

    client.post(
        f"/api/conversations/{convo['id']}/messages",
        json={"content": "Capital of France?"},
    )
    client.post(
        f"/api/conversations/{convo['id']}/messages",
        json={"content": "Population?"},
    )

    provider.generate_conversation_title.assert_called_once_with("Capital of France?")
    fetched = client.get(f"/api/conversations/{convo['id']}")
    assert fetched.json()["title"] == "Capital of France"


def test_send_message_retries_title_generation_after_earlier_failure(monkeypatch):
    """If title generation fails, it's retried on the next message while the
    conversation still has its default title."""
    provider = Mock()
    provider.generate_reply.side_effect = [
        LLMReply(text="Paris."),
        LLMReply(text="About 2.1 million."),
    ]
    provider.generate_conversation_title.side_effect = [
        RuntimeError("boom"),
        "Capital of France",
    ]
    monkeypatch.setattr(chat, "get_llm_provider", lambda: provider)
    convo = client.post("/api/conversations", json={}).json()

    first = client.post(
        f"/api/conversations/{convo['id']}/messages",
        json={"content": "Capital of France?"},
    )
    assert first.status_code == 200
    fetched = client.get(f"/api/conversations/{convo['id']}")
    assert fetched.json()["title"] == "New Conversation"

    second = client.post(
        f"/api/conversations/{convo['id']}/messages",
        json={"content": "Population?"},
    )
    assert second.status_code == 200
    assert provider.generate_conversation_title.call_count == 2

    fetched = client.get(f"/api/conversations/{convo['id']}")
    assert fetched.json()["title"] == "Capital of France"


def test_send_message_to_missing_conversation_returns_404(monkeypatch):
    provider = Mock()
    monkeypatch.setattr(chat, "get_llm_provider", lambda: provider)

    response = client.post(
        "/api/conversations/does-not-exist/messages", json={"content": "hi"}
    )

    assert response.status_code == 404
    provider.generate_reply.assert_not_called()
