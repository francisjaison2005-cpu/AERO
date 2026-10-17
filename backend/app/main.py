"""AirPurify AI FastAPI Backend Service.

Provides real-time IoT air quality telemetry ingestion, device provisioning,
stale device monitoring, EPA AQI compliance, and predictive forecasting interfaces.
Hardened with role-based API security, rate limiting, audit logging, and payload boundaries.
"""

import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from pymongo.database import Database

from app.database import init_db, get_db, check_mongo_health
from app.logging_config import setup_safe_logging, AuditLoggingMiddleware
from app.rate_limiter import RequestSizeLimitMiddleware
from app.schemas import HealthResponse
from app.routes.readings import router as readings_router
from app.routes.devices import router as devices_router
from app.routes.forecasts import router as forecasts_router
from app.routes.alerts import router as alerts_router
from app.services.forecasting import forecasting_service

# Load environment configuration
load_dotenv()

APP_NAME = os.getenv("APP_NAME", "AirPurify AI")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
APP_ENV = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
IS_PRODUCTION = APP_ENV in ("production", "prod")
DEBUG_MODE = os.getenv("DEBUG", "false" if IS_PRODUCTION else "true").lower() == "true"

# Initialize structured safe logging
setup_safe_logging(debug=DEBUG_MODE)
logger = logging.getLogger("airpurify.main")

# CORS development and production configuration
DEFAULT_DEV_CORS = [
    "http://localhost:8443",
    "http://127.0.0.1:8443",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
env_cors = os.getenv("CORS_ORIGINS")
if env_cors:
    allowed_origins = [orig.strip() for orig in env_cors.split(",") if orig.strip()]
elif IS_PRODUCTION:
    # In production, explicit origins MUST be configured
    logger.warning("CORS_ORIGINS not explicitly configured in production; defaulting to empty")
    allowed_origins = []
else:
    allowed_origins = DEFAULT_DEV_CORS

ALLOWED_METHODS = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
ALLOWED_HEADERS = [
    "Content-Type",
    "Authorization",
    "X-API-Key",
    "X-Admin-Key",
    "Accept",
    "Origin",
    "X-Requested-With",
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context for startup and shutdown management."""
    # Initialize database tables automatically in development mode
    init_db()
    enable_model = os.getenv("ENABLE_FORECASTING_MODEL", "").lower()
    if enable_model not in ("false", "0", "no", "disabled"):
        if not os.getenv("PYTEST_CURRENT_TEST"):
            forecasting_service.load_artifacts()
    yield


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "Production-grade backend service for the AirPurify AI air quality platform. "
        "Ingests particulate matter telemetry (PM1.0, PM2.5, PM10) from ESP32 edge stations, "
        "maintains device state, evaluates environmental thresholds, calculates EPA-aligned AQI, "
        "and interfaces with sequence forecasting models."
    ),
    lifespan=lifespan,
    docs_url="/docs" if not IS_PRODUCTION or DEBUG_MODE else None,
    redoc_url="/redoc" if not IS_PRODUCTION or DEBUG_MODE else None,
)

# 1. Payload size limit protection middleware (rejects oversized uploads > 1MB)
app.add_middleware(RequestSizeLimitMiddleware)

# 2. Credential-safe audit logging middleware
app.add_middleware(AuditLoggingMiddleware)

# 3. Restrictive CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Sanitize all unhandled internal exceptions to prevent information leakage."""
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    if DEBUG_MODE:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc), "error_code": "INTERNAL_DEBUG_ERROR"},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred.", "error_code": "INTERNAL_SERVER_ERROR"},
    )


# Register route modules
app.include_router(readings_router)
app.include_router(devices_router)
app.include_router(forecasts_router)
app.include_router(alerts_router)


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Service health check (liveness probe)",
    description="Verify backend availability and database connectivity.",
)
@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Service health check (v1 alias)",
    description="Verify backend availability and database connectivity.",
    include_in_schema=False,
)
def health_check(db: Database = Depends(get_db)) -> HealthResponse:
    """Perform health and database connectivity check."""
    is_connected = check_mongo_health()
    db_status = "connected" if is_connected else "unhealthy"

    return HealthResponse(
        status="healthy" if is_connected else "degraded",
        app_name=APP_NAME,
        version=APP_VERSION,
        database=db_status,
        timestamp=datetime.now(timezone.utc),
    )


@app.get(
    "/api/ready",
    tags=["System"],
    summary="Service readiness probe",
    description="Comprehensive readiness check verifying database connectivity and forecasting pipeline status.",
)
def readiness_check(db: Database = Depends(get_db)):
    """Evaluate full service readiness for load balancer ingress."""
    db_ready = check_mongo_health()
    model_ready = forecasting_service.is_configured
    is_ready = db_ready and model_ready

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "ready": is_ready,
            "app_name": APP_NAME,
            "version": APP_VERSION,
            "environment": APP_ENV,
            "checks": {
                "database": "connected" if db_ready else "unavailable",
                "forecasting_pipeline": "model_ready" if model_ready else "unconfigured",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.get("/", tags=["System"], include_in_schema=False)
def root_redirect():
    """Root endpoint welcoming clients."""
    return {
        "service": APP_NAME,
        "version": APP_VERSION,
        "environment": APP_ENV,
        "docs_url": "/docs" if not IS_PRODUCTION or DEBUG_MODE else "disabled_in_production",
        "health_check": "/api/health",
        "readiness_check": "/api/ready",
    }
