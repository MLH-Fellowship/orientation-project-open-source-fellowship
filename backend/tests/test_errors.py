import logging

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.config import settings
from app.errors import register_exception_handlers
from app.main import app
from app.routes import chat

client = TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    "path, message",
    [
        ("/api/missing", "Not Found"),
        ("/api/conversations/missing", "Conversation not found"),
    ],
)
def test_not_found(path, message):
    response = client.get(path)
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"error": {"code": 404, "message": message}}


@pytest.mark.parametrize(
    "method, path, kwargs, location",
    [
        ("get", "/api/conversations?limit=0", {}, ["query", "limit"]),
        ("get", "/api/conversations?limit=abc", {}, ["query", "limit"]),
        (
            "post",
            "/api/conversations/missing/messages",
            {"json": {}},
            ["body", "content"],
        ),
        (
            "patch",
            "/api/conversations/missing",
            {"json": {"title": "   "}},
            ["body", "title"],
        ),
        (
            "post",
            "/api/conversations",
            {"content": "{", "headers": {"Content-Type": "application/json"}},
            ["body", 1],
        ),
    ],
)
def test_request_validation(method, path, kwargs, location):
    response = client.request(method, path, **kwargs)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == 422
    assert error["message"] == "Request validation failed"
    assert len(error["details"]) == 1
    detail = error["details"][0]
    assert detail["loc"] == location
    assert detail["msg"]
    assert detail["type"]
    assert set(detail) == {"loc", "msg", "type"}


def test_validation_reports_all_invalid_fields():
    response = client.get("/api/conversations?limit=0&offset=-1")

    assert response.status_code == 422
    details = response.json()["error"]["details"]
    assert [detail["loc"] for detail in details] == [
        ["query", "limit"],
        ["query", "offset"],
    ]


def test_validation_does_not_echo_submitted_content():
    response = client.post(
        "/api/conversations/missing/messages",
        json={"content": {"secret": "private message"}},
    )

    assert response.status_code == 422
    detail = response.json()["error"]["details"][0]
    assert detail["loc"] == ["body", "content"]
    assert detail["type"] == "string_type"
    assert "private message" not in response.text


def test_method_not_allowed_preserves_allow_header():
    response = client.put("/api/conversations")
    assert response.status_code == 405
    assert response.headers["allow"]
    assert response.json() == {"error": {"code": 405, "message": "Method Not Allowed"}}


def test_http_exception_preserves_custom_headers():
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/protected")
    def protected():
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    response = TestClient(test_app).get("/protected")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "error": {"code": 401, "message": "Authentication required"}
    }


@pytest.mark.parametrize(
    "origin", [None, settings.frontend_origin, "https://untrusted.example"]
)
def test_unhandled_exception_is_logged_without_exposing_details(
    monkeypatch, caplog, origin
):
    def broken_provider():
        raise RuntimeError("private provider credentials")

    monkeypatch.setattr(chat, "get_llm_provider", broken_provider)
    conversation = client.post("/api/conversations", json={}).json()
    with caplog.at_level(logging.ERROR, logger="app.errors"):
        response = client.post(
            f"/api/conversations/{conversation['id']}/messages",
            json={"content": "hello"},
            headers={"Origin": origin} if origin else {},
        )

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": 500, "message": "Internal server error"}
    }
    assert "private provider credentials" not in response.text
    if origin == settings.frontend_origin:
        assert response.headers["access-control-allow-origin"] == origin
        assert response.headers["access-control-allow-credentials"] == "true"
        assert "Origin" in response.headers["vary"]
    else:
        assert "access-control-allow-origin" not in response.headers
    assert any(
        record.name == "app.errors" and record.exc_info for record in caplog.records
    )


def test_cors_preflight():
    response = client.options(
        "/api/conversations",
        headers={
            "Origin": settings.frontend_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == settings.frontend_origin
    assert "POST" in response.headers["access-control-allow-methods"]


def test_rate_limit_exceeded_uses_error_envelope(caplog):
    for _ in range(10):
        assert client.get("/api/conversations").status_code == 200

    with caplog.at_level(logging.WARNING, logger="app.errors"):
        response = client.get("/api/conversations")

    assert response.status_code == 429
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {
        "error": {"code": 429, "message": "Rate limit exceeded: 10 per 1 minute"}
    }
    assert "Rate limit exceeded during GET /api/conversations" in caplog.text


def test_health_check_is_exempt_from_rate_limiting():
    for _ in range(15):
        assert client.get("/api/health").status_code == 200


def test_rate_limit_bucket_is_shared_across_conversation_ids():
    for _ in range(5):
        assert client.get("/api/conversations/1").status_code == 404
    for _ in range(5):
        assert client.get("/api/conversations/2").status_code == 404

    response = client.get("/api/conversations/2")

    assert response.status_code == 429
