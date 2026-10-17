"""Tests for AirPurify AI 1D-CNN–BiGRU forecasting pipeline and API integration.

Validates:
- Data pipeline validation, chronological splitting, and window generation
- Absence of temporal look-ahead leakage in scaler fitting
- Model loading, inference, and unconfigured fallback behavior
- Evaluation report metrics and baseline verification
- API endpoints: /api/forecasts/status, /api/forecasts/predict, /api/forecasts
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from app.database import get_mongo_db, get_db, init_db
from app.main import app
from app.models import Forecast
from app.services.forecasting import forecasting_service
from ml.config import ARTIFACTS_DIR, FEATURE_COLUMNS, SEQUENCE_LENGTH, TARGET_COLUMN
from ml.data_pipeline import (
    create_sliding_windows,
    fit_and_scale_data,
    split_chronological,
)

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
# Data Pipeline & Leakage Prevention Tests
# -----------------------------------------------------------------------------

def test_chronological_splitting_no_overlap():
    """Verify that dataset splits are strictly sequential with no temporal overlap."""
    dates = pd.date_range("2024-01-01", periods=100, freq="h")
    df = pd.DataFrame({
        "timestamp": dates,
        "pm2.5": np.random.uniform(10, 50, size=100),
        "DEWP": np.random.uniform(-5, 20, size=100),
        "TEMP": np.random.uniform(5, 30, size=100),
        "PRES": np.random.uniform(1000, 1025, size=100),
        "Iws": np.random.uniform(0, 10, size=100),
        "Is": np.zeros(100),
        "Ir": np.zeros(100),
    })

    train_df, val_df, test_df = split_chronological(df, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15)
    assert len(train_df) == 70
    assert len(val_df) == 15
    assert len(test_df) == 15
    assert train_df["timestamp"].max() < val_df["timestamp"].min()
    assert val_df["timestamp"].max() < test_df["timestamp"].min()


def test_scaler_fitted_only_on_training_set():
    """Ensure data scaler is fit strictly on training partition to prevent look-ahead leakage."""
    train_data = pd.DataFrame({
        "pm2.5": [10.0, 20.0, 30.0],
        "DEWP": [0.0, 5.0, 10.0],
        "TEMP": [15.0, 20.0, 25.0],
        "PRES": [1000.0, 1010.0, 1020.0],
        "Iws": [1.0, 2.0, 3.0],
        "Is": [0.0, 0.0, 0.0],
        "Ir": [0.0, 0.0, 0.0],
    })
    # Test partition with out-of-range values
    test_data = pd.DataFrame({
        "pm2.5": [50.0],  # higher than train max (30.0)
        "DEWP": [15.0],
        "TEMP": [30.0],
        "PRES": [1030.0],
        "Iws": [5.0],
        "Is": [0.0],
        "Ir": [0.0],
    })
    val_data = train_data.copy()

    scaled_train, scaled_val, scaled_test, f_scaler, t_scaler = fit_and_scale_data(
        train_data, val_data, test_data, feature_cols=FEATURE_COLUMNS, save_scaler=False
    )

    # In train data, min is 0.0 and max is 1.0
    assert scaled_train[:, 0].min() == pytest.approx(0.0)
    assert scaled_train[:, 0].max() == pytest.approx(1.0)
    # In test data, 50.0 transformed by train scaler (10 to 30) should exceed 1.0 (proving no leakage!)
    assert scaled_test[0, 0] > 1.0


def test_sliding_window_dimensions():
    """Verify shape and alignment of generated temporal sliding windows."""
    seq_len = 24
    horizon = 1
    dummy_data = np.arange(100 * 7, dtype=np.float32).reshape(100, 7)

    X, y = create_sliding_windows(dummy_data, target_idx=0, seq_length=seq_len, horizon=horizon)
    expected_samples = 100 - seq_len - horizon + 1
    assert X.shape == (expected_samples, seq_len, 7)
    assert y.shape == (expected_samples,)
    # Verify temporal alignment: y[0] should equal dummy_data[24, 0]
    assert y[0] == dummy_data[seq_len, 0]


# -----------------------------------------------------------------------------
# Model Loading & Forecasting Service Tests
# -----------------------------------------------------------------------------

def test_service_unloaded_by_default_reports_unconfigured():
    """Verify service returns clean 'model_not_configured' status when unloaded."""
    forecasting_service.unload()
    status = forecasting_service.get_status()
    assert status["status"] == "model_not_configured"
    assert status["is_trained"] is False
    assert "1D-CNN-BiGRU" in status["model_name"]


def test_service_loads_artifacts_when_available():
    """Verify service loads weights, scaler, and real metrics from trained artifacts."""
    loaded = forecasting_service.load_artifacts()
    assert loaded is True
    assert forecasting_service.is_configured is True

    status = forecasting_service.get_status()
    assert status["status"] == "model_ready"
    assert status["is_trained"] is True
    assert status["metrics"] is not None
    assert "mae" in status["metrics"]
    assert "rmse" in status["metrics"]
    assert "r2" in status["metrics"]
    assert status["metrics"]["r2"] > 0.8  # Genuine validated model R2


def test_forecast_inference_generates_valid_predictions():
    """Verify end-to-end forward pass produces realistic PM2.5, AQI, and confidence bounds."""
    forecasting_service.load_artifacts()
    result = forecasting_service.generate_forecast(
        location_id="Engineering Block",
        horizon_hours=3,
        recent_pm25_sequence=[20.0, 22.0, 25.0, 24.0, 21.0] * 5,
    )

    assert result["status"] == "model_ready"
    assert len(result["predictions"]) == 3
    for p in result["predictions"]:
        assert p["predicted_pm25"] >= 0.0
        assert p["predicted_pm10"] >= p["predicted_pm25"]
        assert p["predicted_aqi"] is not None
        assert p["confidence_interval_lower"] <= p["predicted_pm25"]
        assert p["confidence_interval_upper"] >= p["predicted_pm25"]


# -----------------------------------------------------------------------------
# API Route Integration Tests
# -----------------------------------------------------------------------------

def test_api_status_endpoint_with_loaded_model(client: TestClient):
    """Verify GET /api/forecasts/status returns complete model metadata and metrics."""
    forecasting_service.load_artifacts()
    response = client.get("/api/forecasts/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "model_ready"
    assert data["is_trained"] is True
    assert "1D-CNN-BiGRU" in data["model_name"]
    assert data["metrics"]["rmse"] > 0


def test_api_predict_endpoint_creates_and_saves_forecast(client: TestClient):
    """Verify POST /api/forecasts/predict generates and persists predictions."""
    forecasting_service.load_artifacts()
    payload = {
        "location_id": "Station-Alpha",
        "horizon_hours": 2,
        "recent_pm25_sequence": [18.5, 19.0, 21.2],
    }
    response = client.post("/api/forecasts/predict?save_to_db=true", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "model_ready"
    assert len(data["predictions"]) == 2

    # Query GET /api/forecasts to confirm persistence
    get_res = client.get("/api/forecasts?location_id=Station-Alpha")
    assert get_res.status_code == 200
    forecasts = get_res.json()
    assert len(forecasts) == 2
    assert forecasts[0]["predicted_pm25"] is not None
    assert forecasts[0]["predicted_aqi"] is not None
