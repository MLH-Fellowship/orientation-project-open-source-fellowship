from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from google.genai.errors import APIError
from requests.exceptions import ReadTimeout

from app.main import app
from app.routes import chat


@pytest.mark.parametrize(
    "code, expected",
    [
        (400, "rejected"),
        (401, "authenticate"),
        (403, "access"),
        (404, "GEMINI_MODEL"),
        (429, "quota"),
        (503, "unavailable"),
    ],
)
def test_provider_error_is_actionable_without_leaking_details(
    monkeypatch, code, expected
):
    error = APIError(
        code, SimpleNamespace(body_segments=[{"error": {"message": "private-secret"}}])
    )
    monkeypatch.setattr(chat, "get_llm_provider", Mock(side_effect=error))
    client = TestClient(app)
    conversation = client.post("/api/conversations", json={}).json()
    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "hi"},
    )
    assert "event: error" in response.text
    assert expected in response.text
    assert "private-secret" not in response.text
    assert "event: done" not in response.text


def test_timeout_is_actionable(monkeypatch):
    monkeypatch.setattr(
        chat, "get_llm_provider", Mock(side_effect=ReadTimeout("private-url"))
    )
    client = TestClient(app)
    conversation = client.post("/api/conversations", json={}).json()
    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "hi"},
    )
    assert "timed out" in response.text
    assert "504" in response.text
    assert "private-url" not in response.text
