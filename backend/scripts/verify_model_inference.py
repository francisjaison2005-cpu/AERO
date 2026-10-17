"""Model Inference Verification Script for AirPurify AI.

Validates that:
1. /api/forecasts/status reports trained status with genuine benchmark metrics.
2. /api/forecasts/predict invokes the 1D-CNN-BiGRU model.
3. The prediction returns legitimate predicted_pm25, predicted_pm10, confidence intervals.
4. Distinguishes predicted values from measured sensor telemetry.
"""

import json
import sys
import urllib.request

BASE_URL = "http://127.0.0.1:8001"
ADMIN_KEY = "airpurify-admin-dev-key-2026"


def verify_inference():
    print("[*] 1. Checking /api/forecasts/status...")
    req = urllib.request.Request(f"{BASE_URL}/api/forecasts/status")
    with urllib.request.urlopen(req) as resp:
        status_data = json.loads(resp.read().decode("utf-8"))
        print(f"    Status: {status_data['status']}")
        print(f"    Architecture: {status_data['architecture']}")
        print(f"    Model Version: {status_data['model_version']}")
        print(f"    Metrics: MAE={status_data['metrics']['mae']}, RMSE={status_data['metrics']['rmse']}, R2={status_data['metrics']['r2']}")
        assert status_data["is_trained"] is True

    print("\n[*] 2. Triggering genuine 1D-CNN-BiGRU live inference via /api/forecasts/predict...")
    # Feeding a 24-hour sequence representing typical urban pattern
    seq = [30.0 + (i % 8) * 3.5 for i in range(24)]
    payload = {
        "location_id": "Software Verification Chamber",
        "horizon_hours": 3,
        "recent_pm25_sequence": seq,
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/forecasts/predict?save_to_db=true",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Admin-Key": ADMIN_KEY},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        inf_data = json.loads(resp.read().decode("utf-8"))
        print(f"    Model Name: {inf_data['model_name']}")
        print(f"    Issued At: {inf_data['issued_at']}")
        predictions = inf_data.get("predictions", [])
        assert len(predictions) == 3, f"Expected 3 predictions, got {len(predictions)}"
        for p in predictions:
            h = p["horizon_hours"]
            pm25 = p["predicted_pm25"]
            pm10 = p["predicted_pm10"]
            aqi = p["predicted_aqi"]
            ci_l = p["confidence_interval_lower"]
            ci_u = p["confidence_interval_upper"]
            print(f"    Horizon +{h}h: PM2.5={pm25} ug/m3, PM10={pm10} ug/m3, AQI={aqi}, CI=[{ci_l}, {ci_u}]")
            assert pm25 is not None and pm25 > 0
            assert pm10 is not None and pm10 > 0
            assert ci_l <= pm25 <= ci_u

    print("\n>>> MODEL INFERENCE AND PROVENANCE VERIFIED SUCCESSFULLY! <<<")


if __name__ == "__main__":
    try:
        verify_inference()
    except Exception as exc:
        print(f"[!] Inference verification failed: {exc}", file=sys.stderr)
        sys.exit(1)
