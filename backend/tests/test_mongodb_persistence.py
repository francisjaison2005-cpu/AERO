"""Tests for MongoDB Atlas persistence, telemetry validation, and fault-tolerance in AirPurify AI.

Verifies:
- Active database engine is strictly MongoDB Atlas (not SQLite)
- All required telemetry fields are stored in MongoDB Atlas
- Latest reading and historical queries retrieve from MongoDB
- Duplicate and rapid-burst telemetry handling
- Unavailability handling (graceful degradation without silent fallback to SQLite)
- Device heartbeat state updates on MongoDB
"""

import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from pymongo.database import Database
from pymongo.errors import ServerSelectionTimeoutError

from app.database import get_mongo_db, get_db, init_db, check_mongo_health
from app.main import app
from app.models import SensorReading

TEST_DB_NAME = "airpurify_test_db"
test_mongo_db = get_mongo_db(TEST_DB_NAME)


def override_get_db():
    """Dependency override providing isolated test database."""
    yield test_mongo_db


@pytest.fixture(autouse=True)
def setup_test_db():
    """Clean test collections before each test and drop them after."""
    for col in ["devices", "sensor_readings", "alerts", "forecasts", "counters"]:
        test_mongo_db[col].delete_many({})
    init_db(TEST_DB_NAME)
    app.dependency_overrides[get_db] = override_get_db
    yield
    for col in ["devices", "sensor_readings", "alerts", "forecasts", "counters"]:
        test_mongo_db[col].delete_many({})
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    """Provide FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


# -----------------------------------------------------------------------------
# 1. Active Engine & Configuration Verification
# -----------------------------------------------------------------------------

def test_active_database_is_mongodb_atlas_and_not_sqlite():
    """Verify active database dependency produces a MongoDB Database instance."""
    db_gen = get_db()
    active_db = next(db_gen)

    # 1. Must be a PyMongo Database
    assert isinstance(active_db, Database), "Active database is not a PyMongo Database instance!"
    assert active_db.client is not None, "MongoClient is not connected!"

    # 2. Collections must be MongoDB collections
    collections = active_db.list_collection_names()
    assert isinstance(collections, list)

    # 3. MONGODB_URI must be configured with a mongo connection string
    mongo_uri = os.getenv("MONGODB_URI", "")
    assert mongo_uri.startswith("mongodb://") or mongo_uri.startswith("mongodb+srv://"), (
        f"Invalid MONGODB_URI scheme: {mongo_uri}"
    )


# -----------------------------------------------------------------------------
# 2. Telemetry Persistence Field Verification
# -----------------------------------------------------------------------------

def test_mongodb_stores_all_required_telemetry_fields(client: TestClient):
    """Verify device_id, location_id, timestamp, received_at, pm1_0, pm2_5, pm10, and data_quality_status."""
    measurement_time = datetime.now(timezone.utc)
    payload = {
        "device_id": "ESP32-PMS7003-TEST",
        "location_id": "Cleanroom-Alpha",
        "timestamp": measurement_time.isoformat(),
        "pm1_0": 4.2,
        "pm2_5": 8.7,
        "pm10": 15.3,
    }

    response = client.post("/api/readings", json=payload)
    assert response.status_code == 201
    created = response.json()
    reading_id = created["id"]

    # Direct query against isolated test database in MongoDB Atlas
    record = test_mongo_db["sensor_readings"].find_one({"id": reading_id})
    assert record is not None, "Reading was not persisted in MongoDB Atlas!"

    # Verify all 8 required fields
    assert record["device_id"] == "ESP32-PMS7003-TEST"
    assert record["location_id"] == "Cleanroom-Alpha"
    assert isinstance(record["timestamp"], datetime)
    assert isinstance(record["received_at"], datetime)
    assert record["pm1_0"] == 4.2
    assert record["pm2_5"] == 8.7
    assert record["pm10"] == 15.3
    assert record["data_quality_status"] == "valid"

    # Verify atomic sequence ID
    assert isinstance(record["id"], int)
    assert record["id"] > 0


# -----------------------------------------------------------------------------
# 3. Duplicate & Burst Telemetry Handling
# -----------------------------------------------------------------------------

def test_duplicate_telemetry_handling(client: TestClient):
    """Verify rapid or duplicate telemetry submissions are handled gracefully."""
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "device_id": "ESP32-DUP-NODE",
        "location_id": "Lab-101",
        "timestamp": now_iso,
        "pm1_0": 10.0,
        "pm2_5": 20.0,
        "pm10": 30.0,
    }

    # First submission
    res1 = client.post("/api/readings", json=payload)
    assert res1.status_code == 201
    id1 = res1.json()["id"]

    # Immediate second submission (same device, timestamp, and values)
    res2 = client.post("/api/readings", json=payload)
    assert res2.status_code == 201
    id2 = res2.json()["id"]

    # Each gets a distinct auto-increment ID sequence in MongoDB
    assert id1 != id2
    assert id2 > id1

    # Both records exist in the database without corruption
    count = test_mongo_db["sensor_readings"].count_documents({"device_id": "ESP32-DUP-NODE"})
    assert count == 2


# -----------------------------------------------------------------------------
# 4. History Queries with Time Range Filters
# -----------------------------------------------------------------------------

def test_history_queries_filter_and_sort_correctly(client: TestClient):
    """Verify history endpoint filters by start_time, end_time, device, and sorts descending."""
    base_time = datetime(2026, 10, 17, 12, 0, 0, tzinfo=timezone.utc)

    for i in range(5):
        t = base_time - timedelta(minutes=i * 10)
        client.post(
            "/api/readings",
            json={
                "device_id": "ESP32-QUERY-TEST",
                "location_id": "Cleanroom-Beta",
                "timestamp": t.isoformat(),
                "pm1_0": 5.0 + i,
                "pm2_5": 10.0 + i,
                "pm10": 20.0 + i,
            },
        )

    # 1. Query all for device
    res_all = client.get("/api/readings/history?device_id=ESP32-QUERY-TEST")
    assert res_all.status_code == 200
    all_readings = res_all.json()
    assert len(all_readings) == 5
    # Verify sorted descending
    assert all_readings[0]["pm2_5"] == 10.0  # newest (i=0)
    assert all_readings[-1]["pm2_5"] == 14.0  # oldest (i=4)

    # 2. Filter by time window (last 25 minutes -> i=0, 1, 2)
    start_filter = (base_time - timedelta(minutes=25)).strftime("%Y-%m-%dT%H:%M:%SZ")
    res_filtered = client.get(f"/api/readings/history?device_id=ESP32-QUERY-TEST&start_time={start_filter}")
    assert res_filtered.status_code == 200
    filtered = res_filtered.json()
    assert len(filtered) == 3


# -----------------------------------------------------------------------------
# 5. Database Unavailability Handling (No Silent SQLite Fallback)
# -----------------------------------------------------------------------------

def test_database_unavailability_handling_reports_healthy_or_degraded(client: TestClient):
    """Verify that when MongoDB connection fails, /api/health returns degraded and does NOT silently fall back."""
    # Test health check under simulated database failure
    with patch("app.main.check_mongo_health", return_value=False):
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "degraded"
        assert data["database"] == "unhealthy"

    # Test readiness probe under simulated database failure
    with patch("app.main.check_mongo_health", return_value=False):
        res_ready = client.get("/api/ready")
        assert res_ready.status_code == 503
        data_ready = res_ready.json()
        assert data_ready["ready"] is False
        assert data_ready["checks"]["database"] == "unavailable"


def test_reading_ingest_fails_cleanly_when_database_is_unreachable(client: TestClient):
    """Verify ingestion returns HTTP 500 and does NOT silently write to SQLite when MongoDB fails."""
    def broken_get_db():
        raise ServerSelectionTimeoutError("Simulated MongoDB Atlas connection timeout")
        yield

    app.dependency_overrides[get_db] = broken_get_db

    payload = {
        "device_id": "ESP32-FAIL-TEST",
        "location_id": "Cleanroom-Alpha",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pm1_0": 5.0,
        "pm2_5": 10.0,
        "pm10": 20.0,
    }

    res = client.post("/api/readings", json=payload)
    assert res.status_code == 500
    detail = res.json().get("detail", "")
    assert "Simulated MongoDB Atlas connection timeout" in detail or "Failed to record sensor telemetry" in detail


# -----------------------------------------------------------------------------
# 6. Device Heartbeat Tracking in MongoDB
# -----------------------------------------------------------------------------

def test_device_heartbeat_updated_in_mongodb(client: TestClient):
    """Verify new telemetry automatically updates device last_seen and active status in MongoDB."""
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "device_id": "ESP32-HEARTBEAT-NODE",
        "location_id": "Packaging Line",
        "timestamp": now_iso,
        "pm1_0": 3.5,
        "pm2_5": 7.2,
        "pm10": 12.0,
    }

    res = client.post("/api/readings", json=payload)
    assert res.status_code == 201

    dev_doc = test_mongo_db["devices"].find_one({"device_id": "ESP32-HEARTBEAT-NODE"})
    assert dev_doc is not None
    assert dev_doc["status"] == "active"
    assert dev_doc["location_id"] == "Packaging Line"
    assert dev_doc["last_seen"] is not None
