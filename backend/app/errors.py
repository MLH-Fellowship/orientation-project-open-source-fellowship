"""Consistent JSON responses for application and framework errors."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from google.genai.errors import APIError
from httpx import TimeoutException
from requests.exceptions import Timeout
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)


def stream_error(exc: Exception) -> dict:
    """Expose actionable categories without returning private provider details."""
    if isinstance(exc, (Timeout, TimeoutException, TimeoutError)):
        return {"code": 504, "message": "The model request timed out. Try again later."}
    if isinstance(exc, APIError):
        messages = {
            400: "The model rejected the request. Check the API key and model configuration.",
            401: "The model could not authenticate. Check the API key configuration.",
            403: "The API key does not have access to the configured model.",
            404: "The configured model is unavailable. Check GEMINI_MODEL in the backend configuration.",
            429: "The model's rate limit or quota was reached. Check your API quota and try again later.",
        }
        if exc.code in messages:
            return {"code": exc.code, "message": messages[exc.code]}
        if exc.code and exc.code >= 500:
            return {
                "code": 503,
                "message": "The model service is unavailable. Try again later.",
            }
    return {"code": 500, "message": "Could not generate reply"}


async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.status_code, "message": exc.detail}},
        headers=exc.headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": 422,
                "message": "Request validation failed",
                "details": [
                    {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
                    for error in exc.errors()
                ],
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception during %s %s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={"error": {"code": 500, "message": "Internal server error"}},
    )


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(
        "Rate limit exceeded during %s %s: %s",
        request.method,
        request.url.path,
        exc.detail,
    )
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": 429,
                "message": f"Rate limit exceeded: {exc.detail}",
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
