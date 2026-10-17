"""Phase 7 Software Integration & Telemetry Test Client for AirPurify AI.

Strict Pre-IoT Non-Hardware Constraint:
This test client generates purely synthetic software simulation data.
NO physical ESP32 microcontroller or PMS7003 laser sensor is connected.
All test records are tagged 'SYNTHETIC-PHASE7-NODE-01' and 'Software Quality Chamber'.
"""

from datetime import datetime, timezone, timedelta
import json
import sqlite3
import sys
import urllib.error
import urllib.request

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:8001"
DEV_API_KEY = "airpurify-dev-key-2026"
DEV_ADMIN_KEY = "airpurify-admin-dev-key-2026"
DEVICE_ID = "SYNTHETIC-PHASE7-NODE-01"
LOCATION_ID = "Software Quality Chamber"
DB_PATH = "airpurify.db"


def api_request(
    endpoint: str,
    method: str = "GET",
    data: dict = None,
    headers: dict = None,
) -> tuple[int, dict]:
    """Execute HTTP request against AirPurify AI API and return (status_code, response_dict)."""
    url = f"{BASE_URL}{endpoint}"
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as err:
        err_content = err.read().decode("utf-8")
        try:
            err_json = json.loads(err_content)
        except Exception:
            err_json = {"detail": err_content}
        return err.code, err_json


def run_phase7_test_suite():
    print("=" * 80)
    print("AIRPURIFY AI — PHASE 7 SOFTWARE INTEGRATION TEST SUITE")
    print("Pre-IoT Software Freeze: Validating all endpoints & contracts without hardware")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # 1. Probes & Health Checks
    # -------------------------------------------------------------------------
    print("\n[Step 1] Verifying System Health & Readiness Probes...")
    code, res = api_request("/api/health")
    assert code == 200, f"Expected 200, got {code}"
    assert res["status"] == "healthy"
    assert res["database"] == "connected"
    print(f"  ✓ GET /api/health returned healthy: database={res['database']}, version={res['version']}")

    code, res = api_request("/api/ready")
    assert code == 200, f"Expected 200, got {code}"
    assert res["ready"] is True
    print(f"  ✓ GET /api/ready probe confirmed: model={res['checks']['forecasting_pipeline']}, db={res['checks']['database']}")

    # -------------------------------------------------------------------------
    # 2. Authentication & Authorization Enforcement
    # -------------------------------------------------------------------------
    print("\n[Step 2] Testing API Key & Admin Key Enforcement...")
    valid_payload = {
        "device_id": DEVICE_ID,
        "location_id": LOCATION_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pm1_0": 8.0,
        "pm2_5": 14.5,
        "pm10": 26.0,
    }

    # Telemetry without API key -> 401
    code, res = api_request("/api/readings", method="POST", data=valid_payload)
    assert code == 401, f"Expected 401 Unauthorized for missing API key, got {code}"
    print("  ✓ POST /api/readings correctly rejected request with missing X-API-Key (401)")

    # Telemetry with invalid API key -> 401
    code, res = api_request(
        "/api/readings",
        method="POST",
        data=valid_payload,
        headers={"X-API-Key": "invalid-unauthorized-key"},
    )
    assert code == 401, f"Expected 401 Unauthorized for bad API key, got {code}"
    print("  ✓ POST /api/readings correctly rejected request with bogus X-API-Key (401)")

    # Admin predict endpoint without Admin key -> 403
    code, res = api_request(
        "/api/forecasts/predict",
        method="POST",
        data={"location_id": LOCATION_ID, "horizon_hours": 1},
        headers={"X-API-Key": DEV_API_KEY},  # Device key should not suffice for admin
    )
    assert code == 403, f"Expected 403 Forbidden for non-admin on /predict, got {code}"
    print("  ✓ POST /api/forecasts/predict rejected non-admin client (403 Forbidden)")

    # -------------------------------------------------------------------------
    # 3. Valid Telemetry Ingestion & Data Quality Assessment
    # -------------------------------------------------------------------------
    print("\n[Step 3] Submitting Valid Telemetry & Testing Quality Checks...")
    code, res = api_request(
        "/api/readings",
        method="POST",
        data=valid_payload,
        headers={"X-API-Key": DEV_API_KEY},
    )
    assert code == 201, f"Expected 201 Created, got {code}"
    assert res["data_quality_status"] == "valid"
    reading_id_1 = res["id"]
    print(f"  ✓ Standard reading accepted: ID={reading_id_1}, quality={res['data_quality_status']}")

    # Physically questionable reading (PM1.0 > 1.5 * PM2.5)
    questionable_payload = {
        "device_id": DEVICE_ID,
        "location_id": LOCATION_ID,
        "timestamp": (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
        "pm1_0": 38.0,
        "pm2_5": 12.0,  # PM1.0 is 3.1x PM2.5 -> physical anomaly
        "pm10": 25.0,
    }
    code, res = api_request(
        "/api/readings",
        method="POST",
        data=questionable_payload,
        headers={"X-API-Key": DEV_API_KEY},
    )
    assert code == 201, f"Expected 201 Created, got {code}"
    assert res["data_quality_status"] == "questionable"
    print(f"  ✓ Physical anomaly detected correctly: PM1.0=38.0 > 1.5*PM2.5=12.0 -> quality='{res['data_quality_status']}'")

    # -------------------------------------------------------------------------
    # 4. Invalid Telemetry Validation (Schema & Bounds Rejection)
    # -------------------------------------------------------------------------
    print("\n[Step 4] Testing Rejection of Invalid / Malformed Payloads...")
    # Negative value
    neg_payload = valid_payload.copy()
    neg_payload["pm2_5"] = -5.0
    code, res = api_request("/api/readings", method="POST", data=neg_payload, headers={"X-API-Key": DEV_API_KEY})
    assert code == 422, f"Expected 422 Unprocessable Entity for negative PM2.5, got {code}"
    print("  ✓ Negative PM2.5 (-5.0) rejected with 422 Unprocessable Entity")

    # Extreme value exceeding upper limit
    extreme_payload = valid_payload.copy()
    extreme_payload["pm2_5"] = 1500.0  # max is 1000.0
    code, res = api_request("/api/readings", method="POST", data=extreme_payload, headers={"X-API-Key": DEV_API_KEY})
    assert code == 422, f"Expected 422 for PM2.5 > 1000, got {code}"
    print("  ✓ Extreme PM2.5 (1500.0 > 1000) rejected with 422 Unprocessable Entity")

    # Missing required field
    missing_payload = valid_payload.copy()
    del missing_payload["location_id"]
    code, res = api_request("/api/readings", method="POST", data=missing_payload, headers={"X-API-Key": DEV_API_KEY})
    assert code == 422, f"Expected 422 for missing location_id, got {code}"
    print("  ✓ Missing location_id rejected with 422 Unprocessable Entity")

    # -------------------------------------------------------------------------
    # 5. Alert Triggering, Escalation & Duplicate Prevention
    # -------------------------------------------------------------------------
    print("\n[Step 5] Testing Alert Triggering & Duplicate Prevention...")
    # Trigger Warning Alert
    warn_payload = valid_payload.copy()
    warn_payload["timestamp"] = (datetime.now(timezone.utc) + timedelta(seconds=2)).isoformat()
    warn_payload["pm2_5"] = 42.0  # >= 35.0 warning threshold
    code, res = api_request("/api/readings", method="POST", data=warn_payload, headers={"X-API-Key": DEV_API_KEY})
    assert code == 201

    code, alerts = api_request(f"/api/alerts?device_id={DEVICE_ID}&status=active", headers={"X-API-Key": DEV_API_KEY})
    assert code == 200
    pm25_alerts = [a for a in alerts if a["alert_type"] == "HIGH_PM25"]
    assert len(pm25_alerts) == 1
    assert pm25_alerts[0]["severity"] == "warning"
    original_alert_id = pm25_alerts[0]["id"]
    print(f"  ✓ Warning threshold triggered HIGH_PM25 alert ID={original_alert_id} (severity='warning')")

    # Escalate to Critical Alert: should update the existing alert rather than creating a duplicate
    crit_payload = valid_payload.copy()
    crit_payload["timestamp"] = (datetime.now(timezone.utc) + timedelta(seconds=3)).isoformat()
    crit_payload["pm2_5"] = 68.0  # >= 55.0 critical threshold
    code, res = api_request("/api/readings", method="POST", data=crit_payload, headers={"X-API-Key": DEV_API_KEY})
    assert code == 201

    code, alerts = api_request(f"/api/alerts?device_id={DEVICE_ID}&status=active", headers={"X-API-Key": DEV_API_KEY})
    assert code == 200
    pm25_alerts = [a for a in alerts if a["alert_type"] == "HIGH_PM25"]
    assert len(pm25_alerts) == 1, f"Expected exactly 1 active HIGH_PM25 alert (no duplicates), found {len(pm25_alerts)}"
    assert pm25_alerts[0]["id"] == original_alert_id, "Alert ID changed instead of updating existing alert"
    assert pm25_alerts[0]["severity"] == "critical", f"Expected escalation to critical, got {pm25_alerts[0]['severity']}"
    print(f"  ✓ Duplicate prevention verified: Existing alert {original_alert_id} escalated to 'critical' without duplicate creation")

    # Acknowledge alert with admin key
    code, res = api_request(
        f"/api/alerts/{original_alert_id}",
        method="PATCH",
        data={"status": "acknowledged"},
        headers={"X-Admin-Key": DEV_ADMIN_KEY},
    )
    assert code == 200
    assert res["status"] == "acknowledged"
    print(f"  ✓ Alert {original_alert_id} successfully marked 'acknowledged' via Admin auth")

    # -------------------------------------------------------------------------
    # 6. Historical Query & Filtering Verification
    # -------------------------------------------------------------------------
    print("\n[Step 6] Testing Historical Telemetry Queries & Pagination...")
    code, history = api_request(
        f"/api/readings/history?device_id={DEVICE_ID}&limit=5",
        headers={"X-API-Key": DEV_API_KEY},
    )
    assert code == 200
    assert len(history) >= 3
    # Check descending chronological order
    timestamps = [datetime.fromisoformat(r["timestamp"]) for r in history]
    assert timestamps == sorted(timestamps, reverse=True), "History records are not sorted in descending order"
    print(f"  ✓ History query returned {len(history)} records in strict descending chronological order")

    # -------------------------------------------------------------------------
    # 7. Model Status & On-Demand Inference Verification
    # -------------------------------------------------------------------------
    print("\n[Step 7] Testing 1D-CNN–BiGRU Deep Learning Model Inference...")
    code, status = api_request("/api/forecasts/status")
    assert code == 200
    assert status["is_trained"] is True
    assert status["status"] == "model_ready"
    assert status["metrics"]["mae"] == 11.746
    print(f"  ✓ Model engine ready: {status['model_name']} ({status['model_version']}), Test MAE={status['metrics']['mae']} ug/m3")

    # Execute inference
    inference_seq = [20.0 + (i % 6) * 2.0 for i in range(24)]
    code, forecast_res = api_request(
        "/api/forecasts/predict?save_to_db=true",
        method="POST",
        data={
            "location_id": LOCATION_ID,
            "horizon_hours": 3,
            "recent_pm25_sequence": inference_seq,
        },
        headers={"X-Admin-Key": DEV_ADMIN_KEY},
    )
    assert code == 200
    assert len(forecast_res["predictions"]) == 3
    p1 = forecast_res["predictions"][0]
    print(f"  ✓ Inference successful: Horizon +1h PM2.5={p1['predicted_pm25']} ug/m3, AQI={p1['predicted_aqi']}, CI=[{p1['confidence_interval_lower']}, {p1['confidence_interval_upper']}]")

    # -------------------------------------------------------------------------
    # 8. Database Persistence & MongoDB Atlas Verification
    # -------------------------------------------------------------------------
    print("\n[Step 8] Verifying MongoDB Atlas Cloud Persistence...")
    from pymongo import MongoClient
    import os
    mongo_uri = os.getenv("MONGODB_URI", "mongodb+srv://francisjaison2005_db_user:VKi8KDDqGchXfDKS@cluster0.9tdvmma.mongodb.net/?retryWrites=true&w=majority")
    mongo_db_name = os.getenv("MONGODB_DB_NAME", "airpurify_db")
    client = MongoClient(mongo_uri)
    client.admin.command("ping")
    print("  ✓ MongoDB Atlas cluster ping succeeded")

    db = client[mongo_db_name]
    count = db["sensor_readings"].count_documents({"device_id": DEVICE_ID})
    assert count >= 3, f"Expected at least 3 test readings persisted in MongoDB Atlas, found {count}"
    print(f"  ✓ MongoDB Atlas persistence verified: Found {count} persisted records for {DEVICE_ID}")

    print("\n" + "=" * 80)
    print("ALL PHASE 7 SOFTWARE INTEGRATION TESTS PASSED CLEANLY (100% SUCCESS)!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        run_phase7_test_suite()
    except Exception as exc:
        print(f"\n[!] Phase 7 Test Suite Failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
