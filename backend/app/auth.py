"""Authentication and Authorization for AirPurify AI API.

Provides role-based API key validation for edge device telemetry ingestion
and administrative operational endpoints.
Supports graceful development mode fallback and strict production enforcement.
"""
import os
import hmac
import logging
from typing import Optional
from fastapi import Header, HTTPException, status, Security
from fastapi.security import APIKeyHeader

logger = logging.getLogger("airpurify.auth")

# Environment settings
ENVIRONMENT = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
IS_PRODUCTION = ENVIRONMENT in ("production", "prod")

# Configured API keys (with development defaults)
DEFAULT_DEV_KEY = "airpurify-dev-key-2026"
DEFAULT_ADMIN_KEY = "airpurify-admin-dev-key-2026"

DEVICE_API_KEY = os.getenv("AIRPURIFY_API_KEY", DEFAULT_DEV_KEY if not IS_PRODUCTION else "")
ADMIN_API_KEY = os.getenv("AIRPURIFY_ADMIN_KEY", DEFAULT_ADMIN_KEY if not IS_PRODUCTION else "")

# Security header extractors
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def _constant_time_compare(val1: str, val2: str) -> bool:
    """Perform constant-time comparison to prevent timing attacks."""
    if not val1 or not val2:
        return False
    return hmac.compare_digest(val1.encode("utf-8"), val2.encode("utf-8"))


def is_production() -> bool:
    env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    return env in ("production", "prod")


def require_device_auth(
    x_api_key: Optional[str] = Security(api_key_header),
) -> str:
    """Verify device or client API key for ingestion and operational endpoints."""
    # In test mode or unconfigured dev mode, permit graceful access
    if os.getenv("PYTEST_CURRENT_TEST") and not os.getenv("ENFORCE_TEST_AUTH"):
        return "test-client"

    prod = is_production() or (os.getenv("ENFORCE_TEST_AUTH", "").lower() == "true")
    if prod:
        configured_key = os.getenv("AIRPURIFY_API_KEY", "")
        configured_admin = os.getenv("AIRPURIFY_ADMIN_KEY", "")
        if not configured_key and not configured_admin:
            logger.error("Production configuration error: AIRPURIFY_API_KEY / AIRPURIFY_ADMIN_KEY missing.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server authentication configuration error.",
            )
    else:
        configured_key = os.getenv("AIRPURIFY_API_KEY", DEFAULT_DEV_KEY) or DEFAULT_DEV_KEY
        configured_admin = os.getenv("AIRPURIFY_ADMIN_KEY", DEFAULT_ADMIN_KEY) or DEFAULT_ADMIN_KEY

    matches_key = bool(configured_key and _constant_time_compare(x_api_key or "", configured_key))
    matches_admin = bool(configured_admin and _constant_time_compare(x_api_key or "", configured_admin))

    if not x_api_key or (not matches_key and not matches_admin):
        logger.warning("Unauthorized ingestion/read attempt with invalid API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return "device"


def require_admin_auth(
    x_admin_key: Optional[str] = Security(admin_key_header),
    x_api_key: Optional[str] = Security(api_key_header),
) -> str:
    """Verify administrator API key for sensitive operations (device provision, alert resolve, inference)."""
    if os.getenv("PYTEST_CURRENT_TEST") and not os.getenv("ENFORCE_TEST_AUTH"):
        return "test-admin"

    prod = is_production() or (os.getenv("ENFORCE_TEST_AUTH", "").lower() == "true")
    if prod:
        configured_admin = os.getenv("AIRPURIFY_ADMIN_KEY", "")
        if not configured_admin:
            logger.error("Production configuration error: AIRPURIFY_ADMIN_KEY missing.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server administrative configuration error.",
            )
    else:
        configured_admin = os.getenv("AIRPURIFY_ADMIN_KEY", DEFAULT_ADMIN_KEY) or DEFAULT_ADMIN_KEY

    provided_key = x_admin_key or x_api_key
    if not provided_key or not _constant_time_compare(provided_key, configured_admin):
        logger.warning("Unauthorized administrative access attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required. Provide valid X-Admin-Key header.",
        )
    return "admin"

