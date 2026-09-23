"""
FastAPI application entrypoint.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.config import settings
from app.errors import register_exception_handlers
from app.middleware import RequestLoggingMiddleware
from app.routes import chat, health

# Set up global log level and enable console output
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

api = FastAPI(
    title=settings.app_name,
    description="A barebones LLM chat API: conversations, messages, and a pluggable LLM provider.",
    version="0.1.0",
)
register_exception_handlers(api)

# Register new logging middleware
api.add_middleware(RequestLoggingMiddleware)

limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])
api.state.limiter = limiter
api.add_middleware(SlowAPIMiddleware)

api.include_router(health.router, prefix="/api")
api.include_router(chat.router)

app = CORSMiddleware(
    app=api,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
