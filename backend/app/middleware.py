import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Initialize request logger
logger = logging.getLogger("app.request")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Start timer
        start_time = time.perf_counter()

        # Handle request
        response = await call_next(request)

        # Calculate and log duration 
        duration = time.perf_counter() - start_time

        # Log relevant fields
        logger.log(
            log_level_int,
            f"{request.method} {request.url.path} - Status: {response.status_code} - Duration: {duration: .4f}s"
        )

        return response