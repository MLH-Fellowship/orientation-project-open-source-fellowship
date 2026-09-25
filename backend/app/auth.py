import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

SIGNING_ALGO = "HS256"
EXPIRE_MINS = 60

logger = logging.getLogger(__name__)

# Never sign with a value anyone can read in the repo.
_PLACEHOLDER_SECRETS = {"", "your-string-here", "change-this-secret-key"}
if settings.jwt_secret_key in _PLACEHOLDER_SECRETS:
    logger.warning("JWT_SECRET_KEY is not set; using a random key for this run")
    SECRET_KEY = secrets.token_urlsafe(32)
else:
    SECRET_KEY = settings.jwt_secret_key

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer = HTTPBearer()

# Reusable dependency aliases
DbSession = Annotated[Session, Depends(get_db)]
BearerCreds = Annotated[HTTPAuthorizationCredentials, Depends(bearer)]


class Credentials(BaseModel):
    email: str
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def fits_bcrypt(cls, value: str) -> str:
        # bcrypt's limit is 72 bytes, not characters
        if len(value.encode()) > 72:
            raise ValueError("password must be at most 72 bytes")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=EXPIRE_MINS)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        SECRET_KEY,
        algorithm=SIGNING_ALGO,
    )


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(body: Credentials, db: DbSession):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=body.email, hashed_password=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_token(user.id))


@router.post("/login", response_model=TokenResponse)
def login(body: Credentials, db: DbSession):
    user = db.query(User).filter(User.email == body.email).first()
    if (
        not user
        or not user.hashed_password
        or not verify_password(body.password, user.hashed_password)
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenResponse(access_token=create_token(user.id))


def get_current_user(creds: BearerCreds, db: DbSession) -> User:
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[SIGNING_ALGO])
        user = db.get(User, payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        user = None
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
