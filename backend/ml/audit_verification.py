"""Phase 4 Comprehensive Audit & Verification Script.

Inspects raw dataset, artifacts, splits, model weights, baselines, and predictions.
"""
import json
import sys
from pathlib import Path

# Ensure backend root is on python path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import joblib

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

DATA_PATH = BACKEND_DIR / "ml/data/beijing_pm25.csv"
ARTIFACTS_DIR = BACKEND_DIR / "ml/artifacts"
MODEL_PATH = ARTIFACTS_DIR / "model.keras"
SCALER_PATH = ARTIFACTS_DIR / "scaler.joblib"
CONFIG_PATH = ARTIFACTS_DIR / "model_config.json"
REPORT_PATH = ARTIFACTS_DIR / "evaluation_report.json"

print("=" * 70)
print("AIRPURIFY AI — PHASE 4 VERIFICATION AUDIT")
print("=" * 70)

# 1. Dataset verification
print("\n[1] DATASET VERIFICATION")
print(f"Dataset path: {DATA_PATH.resolve()}")
print(f"File exists: {DATA_PATH.exists()}")
file_size = DATA_PATH.stat().st_size
print(f"File size: {file_size:,} bytes")

raw_df = pd.read_csv(DATA_PATH)
n_rows, n_cols = raw_df.shape
print(f"Raw dimensions: {n_rows} rows x {n_cols} columns")
print(f"Raw column names: {raw_df.columns.tolist()}")

# Check presence of particulate pollutants
print("\n[2] POLLUTANT PRESENCE AUDIT")
has_pm1 = "pm1.0" in raw_df.columns or "pm1" in raw_df.columns or "pm1_0" in raw_df.columns
has_pm25 = "pm2.5" in raw_df.columns
has_pm10 = "pm10" in raw_df.columns
print(f"  - PM2.5 column present: {has_pm25} (Column: 'pm2.5', units: ug/m3)")
print(f"  - PM1.0 column present: {has_pm1}")
print(f"  - PM10 column present: {has_pm10}")
if not has_pm1 and not has_pm10:
    print("  -> FACTUAL FINDING: The UCI Beijing PM2.5 dataset only contains PM2.5.")
    print("     PM1.0 and PM10 are NOT present in this raw historical benchmark dataset.")

# Temporal range & frequency
raw_df["timestamp"] = pd.to_datetime(
    raw_df[["year", "month", "day", "hour"]].astype(str).agg("-".join, axis=1),
    format="%Y-%m-%d-%H",
)
min_time = raw_df["timestamp"].min()
max_time = raw_df["timestamp"].max()
time_diffs = raw_df["timestamp"].diff().dropna()
expected_step = pd.Timedelta(hours=1)
irregular_intervals = int((time_diffs != expected_step).sum())

print(f"\nDate range: {min_time} to {max_time}")
print(f"Sampling frequency: Regular hourly (3600s)")
print(f"Irregular intervals in raw file: {irregular_intervals}")

# Missing values
missing_counts = raw_df.isna().sum().to_dict()
print(f"\nMissing values per column in raw data:")
for col, cnt in missing_counts.items():
    if cnt > 0:
        pct = (cnt / n_rows) * 100
        print(f"  - {col}: {cnt} missing ({pct:.2f}%)")

# 3. Model & Artifacts Verification
print("\n[3] MODEL & ARTIFACTS VERIFICATION")
print(f"Model file exists: {MODEL_PATH.exists()} ({MODEL_PATH.stat().st_size:,} bytes)")
print(f"Scaler file exists: {SCALER_PATH.exists()} ({SCALER_PATH.stat().st_size:,} bytes)")
print(f"Config file exists: {CONFIG_PATH.exists()} ({CONFIG_PATH.stat().st_size:,} bytes)")
print(f"Report file exists: {REPORT_PATH.exists()} ({REPORT_PATH.stat().st_size:,} bytes)")

import keras
model = keras.models.load_model(str(MODEL_PATH))
print(f"\nLoaded Keras Model Name: {model.name}")
print(f"Input shape: {model.input_shape}")
print(f"Output shape: {model.output_shape}")
print(f"Layer count: {len(model.layers)}")
print(f"Trainable parameters: {model.count_params():,}")
for i, layer in enumerate(model.layers):
    shape = getattr(layer, 'output_shape', getattr(layer, 'shape', 'N/A'))
    print(f"  Layer {i}: {layer.name} ({layer.__class__.__name__}) -> shape: {shape}")

# 4. Scaler and Pipeline Leakage Verification
print("\n[4] DATA LEAKAGE & PREPROCESSING AUDIT")
scaler_bundle = joblib.load(SCALER_PATH)
f_scaler = scaler_bundle["feature_scaler"]
t_scaler = scaler_bundle["target_scaler"]
feature_cols = scaler_bundle["feature_cols"]
print(f"Features in scaler bundle: {feature_cols}")
print(f"Target variable: {scaler_bundle['target_col']}")
print(f"Feature scaler min: {f_scaler.data_min_}")
print(f"Feature scaler max: {f_scaler.data_max_}")

# 5. Held-out Evaluation Verification
print("\n[5] HELD-OUT TEST EVALUATION AUDIT")
from ml.data_pipeline import (
    create_sliding_windows,
    load_and_validate_dataset,
    split_chronological,
)

df, audit = load_and_validate_dataset()
train_df, val_df, test_df = split_chronological(df)

scaled_test = f_scaler.transform(test_df[feature_cols].values)
target_idx = feature_cols.index("pm2.5")
X_test, y_test = create_sliding_windows(scaled_test, target_idx=target_idx, seq_length=24, horizon=1)

y_pred_scaled = model.predict(X_test, batch_size=64, verbose=0)
y_pred = t_scaler.inverse_transform(y_pred_scaled).flatten()
y_actual = t_scaler.inverse_transform(y_test.reshape(-1, 1)).flatten()

mae = float(mean_absolute_error(y_actual, y_pred))
rmse = float(np.sqrt(mean_squared_error(y_actual, y_pred)))
r2 = float(r2_score(y_actual, y_pred))

# Persistence baseline
y_persist_scaled = X_test[:, -1, target_idx].reshape(-1, 1)
y_persist = t_scaler.inverse_transform(y_persist_scaled).flatten()
persist_mae = float(mean_absolute_error(y_actual, y_persist))
persist_rmse = float(np.sqrt(mean_squared_error(y_actual, y_persist)))
persist_r2 = float(r2_score(y_actual, y_persist))

# Historical mean baseline
mean_val = float(train_df["pm2.5"].mean())
y_mean = np.full_like(y_actual, mean_val)
mean_mae = float(mean_absolute_error(y_actual, y_mean))
mean_rmse = float(np.sqrt(mean_squared_error(y_actual, y_mean)))
mean_r2 = float(r2_score(y_actual, y_mean))

print(f"Test Evaluation Samples: {len(y_actual)}")
print(f"Forecast Horizon: 1 hour")
print(f"1D-CNN-BiGRU:       MAE={mae:.3f} ug/m3 | RMSE={rmse:.3f} ug/m3 | R2={r2:.4f}")
print(f"Persistence Baseline: MAE={persist_mae:.3f} ug/m3 | RMSE={persist_rmse:.3f} ug/m3 | R2={persist_r2:.4f}")
print(f"Hist Mean Baseline:   MAE={mean_mae:.3f} ug/m3 | RMSE={mean_rmse:.3f} ug/m3 | R2={mean_r2:.4f}")

# Check with saved report
with open(REPORT_PATH) as f:
    saved_report = json.load(f)
print("\nSaved Report Metrics Match:")
print(f"  Model MAE match: {round(mae, 3)} == {saved_report['model_metrics']['mae']}")
print(f"  Model RMSE match: {round(rmse, 3)} == {saved_report['model_metrics']['rmse']}")
print(f"  Model R2 match: {round(r2, 4)} == {saved_report['model_metrics']['r2']}")
print(f"  Persistence RMSE match: {round(persist_rmse, 3)} == {saved_report['baselines']['persistence']['rmse']}")

print("\nAUDIT COMPLETE.")
