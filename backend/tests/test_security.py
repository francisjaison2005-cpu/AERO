"""Comprehensive Security & Production Readiness Test Suite.

Covers:
- API key authentication and authorization boundaries
- Ingestion rate limiting and 429 response enforcement
- Request size limit middleware (413 Payload Too Large)
- Error response sanitization (no internal stack trace leakage)
- Liveness (/api/health) and Readiness (/api/ready) health check probes
- Database atomic backup verification
"""
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.database import get_mongo_db, get_db, init_db
from app.main import app
from app.auth import DEFAULT_DEV_KEY, DEFAULT_ADMIN_KEY
from app.rate_limiter import InMemoryRateLimiter
from app.services.forecasting import forecasting_service
from scripts.backup_db import perform_backup

TEST_DB_NAME = "airpurify_test_db"
test_mongo_db = get_mongo_db(TEST_DB_NAME)


def override_get_db():
    yield test_mongo_db


@pytest.fixture
def client():
    for col in ["devices", "sensor_readings", "alerts", "forecasts", "counters"]:
        test_mongo_db[col].delete_many({})
    init_db(TEST_DB_NAME)
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    for col in ["devices", "sensor_readings", "alerts", "forecasts", "counters"]:
        test_mongo_db[col].delete_many({})
    app.dependency_overrides.clear()
    forecasting_service.unload()


# -----------------------------------------------------------------------------
# 1. Authentication and Authorization Tests
# -----------------------------------------------------------------------------

def test_telemetry_ingestion_requires_valid_api_key_when_enforced(client: TestClient, monkeypatch):
    """Verify unauthenticated requests are rejected with 401 when auth is enforced."""
    monkeypatch.setenv("ENFORCE_TEST_AUTH", "true")
    monkeypatch.setenv("AIRPURIFY_API_KEY", "prod-secret-key-xyz")

    payload = {
        "device_id": "EDGE-SEC-01",
        "location_id": "Secure Lab",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pm2_5": 14.5,
        "pm10": 28.0,
    }

    # 1. Missing header -> 401
    res_no_key = client.post("/api/readings", json=payload)
    assert res_no_key.status_code == 401
    assert "Invalid or missing X-API-Key" in res_no_key.json()["detail"]

    # 2. Invalid header -> 401
    res_bad_key = client.post("/api/readings", json=payload, headers={"X-API-Key": "wrong-key"})
    assert res_bad_key.status_code == 401

    # 3. Valid header -> 201 Created
    res_valid = client.post("/api/readings", json=payload, headers={"X-API-Key": "prod-secret-key-xyz"})
    assert res_valid.status_code == 201
    assert res_valid.json()["device_id"] == "EDGE-SEC-01"


def test_administrative_endpoints_require_admin_authorization(client: TestClient, monkeypatch):
    """Verify device registration requires administrative credentials."""
    monkeypatch.setenv("ENFORCE_TEST_AUTH", "true")
    monkeypatch.setenv("AIRPURIFY_ADMIN_KEY", "super-admin-secret-2026")

    device_payload = {
        "device_id": "NEW-PROV-001",
        "device_name": "Provisional Node",
        "location_id": "Server Room",
    }

    # 1. Missing admin credentials -> 403 Forbidden
    res_no_admin = client.post("/api/devices", json=device_payload)
    assert res_no_admin.status_code == 403
    assert "Administrative privileges required" in res_no_admin.json()["detail"]

    # 2. Non-admin device key -> 403 Forbidden
    res_device_key = client.post(
        "/api/devices",
        json=device_payload,
        headers={"X-API-Key": "standard-device-key"},
    )
    assert res_device_key.status_code == 403

    # 3. Valid admin key -> 201 Created
    res_admin = client.post(
        "/api/devices",
        json=device_payload,
        headers={"X-Admin-Key": "super-admin-secret-2026"},
    )
    assert res_admin.status_code == 201
    assert res_admin.json()["device_id"] == "NEW-PROV-001"


# -----------------------------------------------------------------------------
# 2. Rate Limiting Tests
# -----------------------------------------------------------------------------

def test_rate_limiter_sliding_window_enforcement(monkeypatch):
    """Verify in-memory sliding window rate limiter blocks requests above threshold."""
    monkeypatch.setenv("ENFORCE_TEST_RATELIMIT", "true")
    limiter = InMemoryRateLimiter(requests_per_minute=3)
    key = "127.0.0.1:test-route"

    # Make 3 requests -> all allowed
    assert limiter.is_allowed(key)[0] is True
    assert limiter.is_allowed(key)[0] is True
    assert limiter.is_allowed(key)[0] is True

    # 4th request -> blocked
    allowed, retry_after = limiter.is_allowed(key)
    assert allowed is False
    assert retry_after >= 1


# -----------------------------------------------------------------------------
# 3. Request Payload Size Limit Tests
# -----------------------------------------------------------------------------

def test_payload_size_limit_middleware_rejects_oversized_request(client: TestClient):
    """Verify request exceeding 1MB limit is rejected with 413 Payload Too Large."""
    # Create oversized body (> 1MB)
    large_payload = "x" * (1024 * 1024 + 100)
    response = client.post(
        "/api/readings",
        content=large_payload,
        headers={"Content-Length": str(len(large_payload)), "Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert "PAYLOAD_TOO_LARGE" in response.json().get("error_code", "")


# -----------------------------------------------------------------------------
# 4. Error Sanitization & Information Leakage Tests
# -----------------------------------------------------------------------------

def test_unhandled_exceptions_sanitized_in_production(monkeypatch):
    """Verify internal server errors return generic message without stack trace when DEBUG=false."""
    monkeypatch.setenv("DEBUG", "false")

    # Call health check with a simulated broken DB session
    def broken_db():
        raise RuntimeError("Internal database connection terminated with raw table dump [LEAK]")

    app.dependency_overrides[get_db] = broken_db
    try:
        # Use TestClient with raise_server_exceptions=False so 500 response is captured
        safe_client = TestClient(app, raise_server_exceptions=False)
        response = safe_client.get("/api/health")
        assert response.status_code == 500
        data = response.json()
        assert "raw table dump" not in data.get("detail", "")
        assert data.get("detail") == "An internal server error occurred."
    finally:
        app.dependency_overrides.clear()


# -----------------------------------------------------------------------------
# 5. Readiness and Liveness Probes
# -----------------------------------------------------------------------------

def test_liveness_probe_healthy(client: TestClient):
    """Verify /api/health liveness probe returns 200 OK."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readiness_probe_reflects_model_and_db_state(client: TestClient):
    """Verify /api/ready readiness probe checks both database and model state."""
    # When model is unconfigured
    forecasting_service.unload()
    res_unconfigured = client.get("/api/ready")
    assert res_unconfigured.status_code == 503
    assert res_unconfigured.json()["ready"] is False
    assert res_unconfigured.json()["checks"]["database"] == "connected"
    assert res_unconfigured.json()["checks"]["forecasting_pipeline"] == "unconfigured"

    # When model is loaded
    forecasting_service.load_artifacts()
    res_ready = client.get("/api/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["ready"] is True
    assert res_ready.json()["checks"]["forecasting_pipeline"] == "model_ready"


# -----------------------------------------------------------------------------
# 6. Database Atomic Backup Test
# -----------------------------------------------------------------------------

def test_database_backup_generates_valid_sqlite_file(tmp_path: Path):
    """Verify backup utility produces an intact, queryable SQLite backup."""
    # Create test source database with sample record
    src_db = tmp_path / "source.db"
    con = sqlite3.connect(str(src_db))
    con.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, note TEXT)")
    con.execute("INSERT INTO test_data (note) VALUES ('backup_integrity_check')")
    con.commit()
    con.close()

    backup_dir = tmp_path / "backups"
    backup_file = perform_backup(db_path=src_db, backup_dir=backup_dir, max_retentions=3)

    assert backup_file.exists()
    assert backup_file.stat().st_size > 0

    # Query backup to confirm data consistency
    b_con = sqlite3.connect(str(backup_file))
    cur = b_con.cursor()
    cur.execute("SELECT note FROM test_data WHERE id=1")
    row = cur.fetchone()
    b_con.close()

    assert row is not None
    assert row[0] == "backup_integrity_check"


# -----------------------------------------------------------------------------
# 7. Sensitive Write Endpoints & Input Validation Tests
# -----------------------------------------------------------------------------

def test_alert_patch_requires_admin_authorization(client: TestClient, monkeypatch):
    """Verify alert modification rejects unauthenticated/non-admin requests."""
    monkeypatch.setenv("ENFORCE_TEST_AUTH", "true")
    monkeypatch.setenv("AIRPURIFY_ADMIN_KEY", "admin-secret-test-999")

    # 1. Missing admin credentials -> 403 Forbidden
    res_no_auth = client.patch("/api/alerts/1", json={"status": "resolved"})
    assert res_no_auth.status_code == 403

    # 2. Invalid admin credentials -> 403 Forbidden
    res_bad_auth = client.patch(
        "/api/alerts/1",
        json={"status": "resolved"},
        headers={"X-Admin-Key": "wrong-admin-key"},
    )
    assert res_bad_auth.status_code == 403


def test_forecast_predict_requires_admin_authorization(client: TestClient, monkeypatch):
    """Verify on-demand AI inference trigger rejects unauthenticated/non-admin requests."""
    monkeypatch.setenv("ENFORCE_TEST_AUTH", "true")
    monkeypatch.setenv("AIRPURIFY_ADMIN_KEY", "admin-secret-test-999")

    inference_payload = {"location_id": "Lab-01", "horizon_hours": 1}

    # 1. Missing admin credentials -> 403 Forbidden
    res_no_auth = client.post("/api/forecasts/predict", json=inference_payload)
    assert res_no_auth.status_code == 403

    # 2. Valid admin credentials -> Proceeds past auth check
    forecasting_service.load_artifacts()
    res_valid_auth = client.post(
        "/api/forecasts/predict",
        json=inference_payload,
        headers={"X-Admin-Key": "admin-secret-test-999"},
    )
    assert res_valid_auth.status_code in (200, 201)
    assert res_valid_auth.json()["location_id"] == "Lab-01"


def test_invalid_telemetry_input_rejected_by_schema_validation(client: TestClient):
    """Verify invalid or physically impossible inputs are rejected with 422 Unprocessable Entity."""
    # 1. Negative PM2.5 value
    res_negative = client.post(
        "/api/readings",
        json={
            "device_id": "TEST-01",
            "location_id": "Room-A",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pm2_5": -5.0,
            "pm10": 20.0,
        },
    )
    assert res_negative.status_code == 422

    # 2. Non-numeric PM2.5 value
    res_string_pm = client.post(
        "/api/readings",
        json={
            "device_id": "TEST-01",
            "location_id": "Room-A",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pm2_5": "not-a-number",
            "pm10": 20.0,
        },
    )
    assert res_string_pm.status_code == 422

    # 3. Missing required field (timestamp)
    res_missing_time = client.post(
        "/api/readings",
        json={
            "device_id": "TEST-01",
            "location_id": "Room-A",
            "pm2_5": 25.0,
            "pm10": 40.0,
        },
    )
    assert res_missing_time.status_code == 422


def test_cors_options_preflight_response(client: TestClient):
    """Verify CORS preflight OPTIONS returns allowed methods and headers."""
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:8443",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:8443"
    assert "GET" in response.headers.get("access-control-allow-methods", "")

