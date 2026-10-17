"""Automated test suite for AirPurify AI backend.

Covers:
- Health check and database connectivity
- ESP32 telemetry ingestion
- Database persistence verification
- Latest reading and historical query retrieval
- Invalid and missing payload validation
- Duplicate alert prevention
- Forecasting model unconfigured state
- EPA AQI calculation service verification
"""

import os
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from app.database import get_mongo_db, get_db, init_db
from app.main import app
from app.models import SensorReading, Device, Alert
from app.services.aqi import calculate_instantaneous_aqi, calculate_official_nowcast_aqi
from app.services.forecasting import forecasting_service

TEST_DB_NAME = "airpurify_test_db"
test_mongo_db = get_mongo_db(TEST_DB_NAME)


def override_get_db():
    """Dependency override providing isolated test session."""
    yield test_mongo_db


@pytest.fixture(autouse=True)
def setup_test_db():
    """Clean test collections before each test and drop them after."""
    for col in ["devices", "sensor_readings", "alerts", "forecasts", "counters"]:
        test_mongo_db[col].delete_many({})
    init_db(TEST_DB_NAME)
    app.dependency_overrides[get_db] = override_get_db
    forecasting_service.unload()
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
# 1. Health Endpoint Tests
# -----------------------------------------------------------------------------

def test_health_check(client: TestClient):
    """Verify health endpoint reports system status and database connectivity."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "AirPurify AI"
    assert data["database"] == "connected"
    assert "timestamp" in data


def test_health_check_v1_alias(client: TestClient):
    """Verify /api/v1/health alias endpoint returns identical healthy status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "AirPurify AI"
    assert data["database"] == "connected"
    assert "timestamp" in data


# -----------------------------------------------------------------------------
# 2. Sensor Reading Ingestion & Persistence Tests
# -----------------------------------------------------------------------------

def test_sensor_reading_submission_success(client: TestClient):
    """Test successful ingestion of ESP32 sensor reading."""
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "device_id": "ESP32-001",
        "location_id": "Engineering Block",
        "timestamp": now_iso,
        "pm1_0": 9.2,
        "pm2_5": 18.5,
        "pm10": 34.0,
    }

    response = client.post("/api/readings", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["device_id"] == "ESP32-001"
    assert data["location_id"] == "Engineering Block"
    assert data["pm1_0"] == 9.2
    assert data["pm2_5"] == 18.5
    assert data["pm10"] == 34.0
    assert data["data_quality_status"] == "valid"
    assert "received_at" in data


def test_database_persistence(client: TestClient):
    """Verify sensor reading is truly committed to the database."""
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "device_id": "ESP32-PERSIST",
        "location_id": "Server Room",
        "timestamp": now_iso,
        "pm1_0": 5.0,
        "pm2_5": 12.0,
        "pm10": 20.0,
    }
    post_res = client.post("/api/readings", json=payload)
    assert post_res.status_code == 201
    reading_id = post_res.json()["id"]

    # Query directly via MongoDB test database
    db_record = test_mongo_db["sensor_readings"].find_one({"id": reading_id})
    assert db_record is not None
    assert db_record["device_id"] == "ESP32-PERSIST"
    assert db_record["pm2_5"] == 12.0
    assert db_record["pm10"] == 20.0

    # Verify device record was also auto-registered
    device = test_mongo_db["devices"].find_one({"device_id": "ESP32-PERSIST"})
    assert device is not None
    assert device["status"] == "active"
    assert device["location_id"] == "Server Room"


# -----------------------------------------------------------------------------
# 3. Reading Query Tests (Latest & History)
# -----------------------------------------------------------------------------

def test_get_latest_reading(client: TestClient):
    """Verify retrieval of the latest reading for a device or overall."""
    base_time = datetime.now(timezone.utc)

    # Ingest two readings with different timestamps
    payload_old = {
        "device_id": "ESP32-002",
        "location_id": "Library",
        "timestamp": (base_time - timedelta(minutes=10)).isoformat(),
        "pm1_0": 6.0,
        "pm2_5": 14.0,
        "pm10": 22.0,
    }
    payload_new = {
        "device_id": "ESP32-002",
        "location_id": "Library",
        "timestamp": base_time.isoformat(),
        "pm1_0": 11.0,
        "pm2_5": 25.0,
        "pm10": 45.0,
    }

    client.post("/api/readings", json=payload_old)
    client.post("/api/readings", json=payload_new)

    response = client.get("/api/readings/latest?device_id=ESP32-002")
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == "ESP32-002"
    assert data["pm2_5"] == 25.0


def test_get_latest_reading_not_found(client: TestClient):
    """Verify 404 response when no reading matches."""
    response = client.get("/api/readings/latest?device_id=NON_EXISTENT")
    assert response.status_code == 404
    assert "No sensor readings found" in response.json()["detail"]


def test_get_reading_history(client: TestClient):
    """Verify historical readings retrieval with ordering and limits."""
    base_time = datetime.now(timezone.utc)
    for i in range(5):
        client.post(
            "/api/readings",
            json={
                "device_id": "ESP32-HIST",
                "location_id": "Chemistry Lab",
                "timestamp": (base_time - timedelta(minutes=i)).isoformat(),
                "pm1_0": 5.0 + i,
                "pm2_5": 10.0 + i,
                "pm10": 20.0 + i,
            },
        )

    response = client.get("/api/readings/history?device_id=ESP32-HIST&limit=3")
    assert response.status_code == 200
    readings = response.json()
    assert len(readings) == 3
    # Check descending order by timestamp
    assert readings[0]["pm2_5"] == 10.0  # newest (i=0)


# -----------------------------------------------------------------------------
# 4. Validation & Error Handling Tests
# -----------------------------------------------------------------------------

def test_invalid_negative_sensor_values(client: TestClient):
    """Verify validation rejection on negative PM concentrations."""
    payload = {
        "device_id": "ESP32-FAIL",
        "location_id": "Outdoor",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pm1_0": -5.0,
        "pm2_5": -10.0,
        "pm10": 20.0,
    }
    response = client.post("/api/readings", json=payload)
    assert response.status_code == 422


def test_missing_required_fields(client: TestClient):
    """Verify rejection when mandatory fields are omitted."""
    # Missing pm2_5
    payload = {
        "device_id": "ESP32-FAIL",
        "location_id": "Outdoor",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pm10": 20.0,
    }
    response = client.post("/api/readings", json=payload)
    assert response.status_code == 422

    # Empty device_id
    payload_empty_device = {
        "device_id": "",
        "location_id": "Outdoor",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pm2_5": 15.0,
        "pm10": 20.0,
    }
    res2 = client.post("/api/readings", json=payload_empty_device)
    assert res2.status_code == 422


# -----------------------------------------------------------------------------
# 5. Alerts & Duplicate Prevention Tests
# -----------------------------------------------------------------------------

def test_alert_generation_and_duplicate_prevention(client: TestClient):
    """Verify alert triggers on high PM2.5 and duplicate active alerts are prevented."""
    high_pm25_payload = {
        "device_id": "ESP32-ALERT-DEV",
        "location_id": "Workshop",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pm1_0": 40.0,
        "pm2_5": 65.0,  # Exceeds critical threshold (> 55)
        "pm10": 110.0,
    }

    # Ingest twice
    res1 = client.post("/api/readings", json=high_pm25_payload)
    assert res1.status_code == 201

    res2 = client.post("/api/readings", json=high_pm25_payload)
    assert res2.status_code == 201

    # Check alerts via API
    alerts_res = client.get("/api/alerts?device_id=ESP32-ALERT-DEV&status=active")
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()

    # Must NOT produce duplicate active HIGH_PM25 alerts
    pm25_alerts = [a for a in alerts if a["alert_type"] == "HIGH_PM25"]
    assert len(pm25_alerts) == 1
    assert pm25_alerts[0]["severity"] == "critical"


def test_alert_status_patch(client: TestClient):
    """Verify alert status can be acknowledged or resolved."""
    high_payload = {
        "device_id": "ESP32-PATCH-ALERT",
        "location_id": "Workshop",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pm2_5": 70.0,
        "pm10": 120.0,
    }
    client.post("/api/readings", json=high_payload)

    alerts = client.get("/api/alerts?device_id=ESP32-PATCH-ALERT").json()
    assert len(alerts) >= 1
    alert_id = alerts[0]["id"]

    patch_res = client.patch(f"/api/alerts/{alert_id}", json={"status": "resolved"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "resolved"


# -----------------------------------------------------------------------------
# 6. Forecasting Model Status Tests
# -----------------------------------------------------------------------------

def test_forecasting_model_status_unconfigured(client: TestClient):
    """Verify model status correctly reports model_not_configured without fabricating predictions."""
    response = client.get("/api/forecasts/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "model_not_configured"
    assert data["is_trained"] is False
    assert "1D-CNN-BiGRU" in data["model_name"]
    assert "not yet configured or trained" in data["message"]


def test_forecasts_endpoint_empty_when_unconfigured(client: TestClient):
    """Verify forecasts list returns empty when model is unconfigured."""
    response = client.get("/api/forecasts?location_id=Engineering%20Block")
    assert response.status_code == 200
    assert response.json() == []


# -----------------------------------------------------------------------------
# 7. AQI Calculation Service Tests
# -----------------------------------------------------------------------------

def test_aqi_service_handles_missing_measurements():
    """Verify AQI service returns unavailable status when measurements are missing."""
    result = calculate_instantaneous_aqi(pm2_5=None, pm10=None)
    assert result["status"] == "unavailable"
    assert result["aqi"] is None
    assert "Missing required" in result["reason"]


def test_aqi_service_calculates_indicative_values():
    """Verify AQI formula calculates proper category for known concentration."""
    # PM2.5 = 10.0 µg/m³ is in "Good" range (0 - 12.0)
    res_good = calculate_instantaneous_aqi(pm2_5=10.0, pm10=20.0)
    assert res_good["status"] == "calculated"
    assert res_good["category"] == "Good"
    assert 0 <= res_good["aqi"] <= 50

    # PM2.5 = 60.0 µg/m³ is in "Unhealthy" range (55.5 - 150.4)
    res_unhealthy = calculate_instantaneous_aqi(pm2_5=60.0, pm10=50.0)
    assert res_unhealthy["status"] == "calculated"
    assert res_unhealthy["category"] == "Unhealthy"
    assert 151 <= res_unhealthy["aqi"] <= 200


def test_official_nowcast_requires_full_window():
    """Verify official NowCast returns unavailable when fewer than 12 hours provided."""
    few_readings = [12.0, 14.0, 15.0]  # Only 3 hours
    result = calculate_official_nowcast_aqi(few_readings)
    assert result["status"] == "unavailable"
    assert "Insufficient averaging period" in result["reason"]


def test_cpcb_aqi_rejects_sub_24h_averaging():
    """Verify CPCB NAQI rejects instantaneous or sub-24h readings."""
    from app.services.aqi import calculate_official_cpcb_aqi
    pollutants = {"PM2.5": 25.0, "PM10": 45.0, "NO2": 30.0}
    result = calculate_official_cpcb_aqi(pollutants, is_24h_average=False)
    assert result["status"] == "unavailable"
    assert "CPCB Compliance" in result["reason"]
    assert "24-hour averaging period" in result["reason"]


def test_cpcb_aqi_requires_minimum_three_pollutants():
    """Verify CPCB NAQI requires at least 3 monitored pollutants."""
    from app.services.aqi import calculate_official_cpcb_aqi
    # Only 2 pollutants provided
    pollutants = {"PM2.5": 25.0, "PM10": 45.0}
    result = calculate_official_cpcb_aqi(pollutants, is_24h_average=True)
    assert result["status"] == "unavailable"
    assert "at least 3 pollutants" in result["reason"]


def test_cpcb_aqi_requires_particulate_matter():
    """Verify CPCB NAQI requires at least one particulate matter pollutant (PM2.5 or PM10)."""
    from app.services.aqi import calculate_official_cpcb_aqi
    # 3 pollutants, but none are PM2.5 or PM10
    pollutants = {"SO2": 20.0, "NO2": 35.0, "CO": 1.5}
    result = calculate_official_cpcb_aqi(pollutants, is_24h_average=True)
    assert result["status"] == "unavailable"
    assert "PM2.5 or PM10" in result["reason"]


def test_cpcb_aqi_calculates_when_regulatory_criteria_satisfied():
    """Verify CPCB NAQI correctly computes AQI when all 24h regulatory criteria are satisfied."""
    from app.services.aqi import calculate_official_cpcb_aqi
    pollutants = {"PM2.5": 25.0, "PM10": 40.0, "NO2": 30.0}
    result = calculate_official_cpcb_aqi(pollutants, is_24h_average=True)
    assert result["status"] == "calculated"
    assert result["category"] == "Good"
    assert 0 <= result["aqi"] <= 50
    assert result["averaging_period"] == "24-hour"

