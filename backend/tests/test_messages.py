from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

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
    provider.generate_reply.return_value = "Hello back"
    monkeypatch.setattr(chat, "get_llm_provider", lambda: provider)
    convo = client.post("/api/conversations", json={}).json()

    response = client.post(
        f"/api/conversations/{convo['id']}/messages", json={"content": content}
    )

    assert response.status_code == 200
    assert response.json()["content"] == "Hello back"
    provider.generate_reply.assert_called_once_with(
        [{"role": "user", "content": expected}]
    )
    fetched = client.get(f"/api/conversations/{convo['id']}")
    user_messages = [m for m in fetched.json()["messages"] if m["role"] == "user"]
    assert len(user_messages) == 1
    assert user_messages[0]["content"] == expected
