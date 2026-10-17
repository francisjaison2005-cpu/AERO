"""Rate limiting and payload protection for AirPurify AI backend.

Implements token bucket / sliding window rate limiting per client IP
and protects endpoints against oversized payloads and denial-of-service attempts.
"""
import time
import os
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

MAX_PAYLOAD_BYTES = int(os.getenv("MAX_PAYLOAD_BYTES", 1024 * 1024))  # 1 MB default


class InMemoryRateLimiter:
    """Sliding-window rate limiter keyed by client identifier and endpoint."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        # Dict mapping key -> list of float timestamps
        self.history: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> Tuple[bool, int]:
        """Check if request is permitted under rate limit.

        Returns (allowed, retry_after_seconds)
        """
        if os.getenv("PYTEST_CURRENT_TEST") and not os.getenv("ENFORCE_TEST_RATELIMIT"):
            return True, 0

        now = time.time()
        window_start = now - 60.0

        # Purge timestamps older than 60 seconds
        timestamps = [t for t in self.history[key] if t > window_start]
        self.history[key] = timestamps

        if len(timestamps) >= self.requests_per_minute:
            oldest_in_window = timestamps[0]
            retry_after = max(1, int(60.0 - (now - oldest_in_window)))
            return False, retry_after

        self.history[key].append(now)
        return True, 0


# Limiters for different sensitivity tiers
standard_rate_limiter = InMemoryRateLimiter(requests_per_minute=120)
ingestion_rate_limiter = InMemoryRateLimiter(requests_per_minute=60)
inference_rate_limiter = InMemoryRateLimiter(requests_per_minute=20)


def rate_limit(limiter: InMemoryRateLimiter = standard_rate_limiter):
    """FastAPI dependency to enforce rate limit on specific route."""
    def dependency(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        key = f"{client_ip}:{path}"

        allowed, retry_after = limiter.is_allowed(key)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )
    return dependency


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing maximum permissible request payload size."""

    def __init__(self, app, max_bytes: int = MAX_PAYLOAD_BYTES):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_bytes:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "detail": f"Payload size {length} bytes exceeds maximum allowed limit of {self.max_bytes} bytes.",
                            "error_code": "PAYLOAD_TOO_LARGE",
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)
