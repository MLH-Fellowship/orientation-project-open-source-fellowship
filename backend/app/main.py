"""
FastAPI application entrypoint.

Run with:
    uvicorn app.main:app --reload --port 8000
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.middleware import RequestLoggingMiddleware
from app.routes import chat, health

# Set up global log level and enable console output
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

# Register new logging middleware
app.add_middleware(RequestLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(chat.router)
