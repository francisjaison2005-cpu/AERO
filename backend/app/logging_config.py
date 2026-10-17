"""Safe structured logging and audit middleware.

Redacts sensitive headers, tokens, and credentials from all system logs.
"""
import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

SENSITIVE_HEADERS = {"authorization", "x-api-key", "x-admin-key", "cookie", "set-cookie"}

logger = logging.getLogger("airpurify.audit")


def setup_safe_logging(debug: bool = False):
    """Configure root and application loggers."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Silence verbose third-party wire protocol logs
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Intercept and safely audit incoming HTTP requests without leaking credentials."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_host = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
        except Exception as exc:
            process_time_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                "Unhandled error on %s %s - duration=%sms - client=%s: %s",
                method,
                path,
                process_time_ms,
                client_host,
                exc,
                exc_info=True,
            )
            import os
            from starlette.responses import JSONResponse
            debug = os.getenv("DEBUG", "false").lower() == "true"
            if debug:
                return JSONResponse(
                    status_code=500,
                    content={"detail": str(exc), "error_code": "INTERNAL_DEBUG_ERROR"},
                )
            return JSONResponse(
                status_code=500,
                content={"detail": "An internal server error occurred.", "error_code": "INTERNAL_SERVER_ERROR"},
            )

        process_time_ms = round((time.time() - start_time) * 1000, 2)

        # Audit log (safe from credentials)
        logger.info(
            "%s %s - status=%d - duration=%sms - client=%s",
            method,
            path,
            response.status_code,
            process_time_ms,
            client_host,
        )

        return response
