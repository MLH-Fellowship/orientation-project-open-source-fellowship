from conftest import TestingSessionLocal
from fastapi.testclient import TestClient

from app.main import app
from app.models import Message

client = TestClient(app)


def _create_conversation(title=None):
    payload = {"title": title} if title else {}
    return client.post("/api/conversations", json=payload)


def test_list_conversations_default_pagination():
    for i in range(3):
        _create_conversation(f"Convo {i}")

    response = client.get("/api/conversations")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert len(body["items"]) == 3


def test_list_conversations_respects_limit_and_offset():
    for i in range(5):
        _create_conversation(f"Convo {i}")

    response = client.get("/api/conversations", params={"limit": 2, "offset": 1})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert len(body["items"]) == 2


def test_list_conversations_rejects_invalid_limit():
    response = client.get("/api/conversations", params={"limit": 0})
    assert response.status_code == 422

    response = client.get("/api/conversations", params={"limit": 101})
    assert response.status_code == 422


def test_rename_conversation():
    convo = _create_conversation("Old title").json()

    response = client.patch(
        f"/api/conversations/{convo['id']}", json={"title": "New title"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == convo["id"]
    assert body["title"] == "New title"

    fetched = client.get(f"/api/conversations/{convo['id']}")
    assert fetched.json()["title"] == "New title"


def test_rename_conversation_strips_whitespace():
    convo = _create_conversation("Old title").json()

    response = client.patch(
        f"/api/conversations/{convo['id']}", json={"title": "  Trimmed  "}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Trimmed"


def test_rename_conversation_rejects_empty_title():
    convo = _create_conversation("Old title").json()

    response = client.patch(f"/api/conversations/{convo['id']}", json={"title": ""})
    assert response.status_code == 422

    response = client.patch(f"/api/conversations/{convo['id']}", json={"title": "   "})
    assert response.status_code == 422


def test_rename_conversation_rejects_too_long_title():
    convo = _create_conversation("Old title").json()

    response = client.patch(
        f"/api/conversations/{convo['id']}", json={"title": "x" * 201}
    )
    assert response.status_code == 422


def test_rename_conversation_accepts_title_that_only_exceeds_limit_with_padding():
    convo = _create_conversation("Old title").json()

    response = client.patch(
        f"/api/conversations/{convo['id']}", json={"title": ("x" * 200) + "   "}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "x" * 200


def test_rename_conversation_not_found():
    response = client.patch(
        "/api/conversations/does-not-exist", json={"title": "New title"}
    )
    assert response.status_code == 404


def test_delete_conversation():
    convo = _create_conversation("To delete").json()

    response = client.delete(f"/api/conversations/{convo['id']}")
    assert response.status_code == 204
    assert response.content == b""

    fetched = client.get(f"/api/conversations/{convo['id']}")
    assert fetched.status_code == 404


def test_delete_conversation_cascades_messages():
    convo = _create_conversation("With messages").json()

    db = TestingSessionLocal()
    try:
        db.add(Message(conversation_id=convo["id"], role="user", content="hello"))
        db.commit()
        assert db.query(Message).filter_by(conversation_id=convo["id"]).count() > 0
    finally:
        db.close()

    response = client.delete(f"/api/conversations/{convo['id']}")
    assert response.status_code == 204

    db = TestingSessionLocal()
    try:
        assert db.query(Message).filter_by(conversation_id=convo["id"]).count() == 0
    finally:
        db.close()


def test_delete_conversation_not_found():
    response = client.delete("/api/conversations/does-not-exist")
    assert response.status_code == 404
