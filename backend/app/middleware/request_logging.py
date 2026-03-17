import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/favicon.ico"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        extra = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else "unknown",
        }

        logger.info("Request started", extra=extra)

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.exception(
                "Request failed with unhandled exception",
                extra={**extra, "duration_ms": duration_ms, "status_code": 500},
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        log_extra = {
            **extra,
            "duration_ms": duration_ms,
            "status_code": response.status_code,
        }

        if response.status_code >= 500:
            logger.error("Request completed with server error", extra=log_extra)
        elif response.status_code >= 400:
            logger.warning("Request completed with client error", extra=log_extra)
        else:
            logger.info("Request completed", extra=log_extra)

        return response
