import jwt
import pytest
from conftest import TestingSessionLocal
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from app.models import User

client = TestClient(app)

CREDS = {"email": "ada@example.com", "password": "correct horse"}


def _signup(creds=CREDS):
    return client.post("/api/auth/signup", json=creds)


def _current_user(token):
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with TestingSessionLocal() as db:
        return auth.get_current_user(creds, db)


def test_signup_stores_a_hash_and_returns_a_token():
    response = _signup()

    assert response.status_code == 201
    assert response.json()["token_type"] == "bearer"
    with TestingSessionLocal() as db:
        user = db.query(User).filter_by(email=CREDS["email"]).one()
        assert user.hashed_password != CREDS["password"]
        assert auth.verify_password(CREDS["password"], user.hashed_password)


def test_signup_rejects_a_duplicate_email():
    _signup()

    assert _signup().status_code == 409


def test_signup_rejects_a_password_over_72_bytes():
    # 72 characters but 144 bytes, which bcrypt can't take
    response = _signup({"email": "b@example.com", "password": "é" * 72})

    assert response.status_code == 422


def test_login_returns_a_token_for_the_right_password():
    _signup()

    response = client.post("/api/auth/login", json=CREDS)

    assert response.status_code == 200
    assert response.json()["access_token"]


@pytest.mark.parametrize(
    "creds",
    [
        {"email": CREDS["email"], "password": "wrong"},
        {"email": "nobody@example.com", "password": "wrong"},
    ],
)
def test_login_rejects_bad_credentials_the_same_way(creds):
    _signup()

    response = client.post("/api/auth/login", json=creds)

    assert response.status_code == 401


def test_current_user_resolves_from_a_login_token():
    _signup()
    token = client.post("/api/auth/login", json=CREDS).json()["access_token"]

    assert _current_user(token).email == CREDS["email"]


def test_current_user_rejects_a_token_signed_with_another_key():
    _signup()
    with TestingSessionLocal() as db:
        user_id = db.query(User).filter_by(email=CREDS["email"]).one().id
    forged = jwt.encode({"sub": user_id}, "not-the-key", algorithm="HS256")

    with pytest.raises(HTTPException) as exc:
        _current_user(forged)
    assert exc.value.status_code == 401
