"""Training and evaluation pipeline for AirPurify AI forecasting model.

Trains the 1D-CNN-BiGRU architecture on training data, validates on validation split,
and rigorously benchmarks against persistence and mean baselines on the held-out test set.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Tuple

import joblib
import keras
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

try:
    from ml.config import (
        BATCH_SIZE,
        CONFIG_PATH,
        DATASET_PATH,
        DATASET_PROVENANCE,
        EARLY_STOPPING_PATIENCE,
        EPOCHS,
        FEATURE_COLUMNS,
        FORECAST_HORIZON,
        LEARNING_RATE,
        MODEL_PATH,
        REPORT_PATH,
        SCALER_PATH,
        SEQUENCE_LENGTH,
        TARGET_COLUMN,
    )
    from ml.data_pipeline import (
        create_sliding_windows,
        download_dataset,
        fit_and_scale_data,
        load_and_validate_dataset,
        split_chronological,
    )
    from ml.model import build_1d_cnn_bigru_model, get_model_metadata
except ImportError:
    from backend.ml.config import (
        BATCH_SIZE,
        CONFIG_PATH,
        DATASET_PATH,
        DATASET_PROVENANCE,
        EARLY_STOPPING_PATIENCE,
        EPOCHS,
        FEATURE_COLUMNS,
        FORECAST_HORIZON,
        LEARNING_RATE,
        MODEL_PATH,
        REPORT_PATH,
        SCALER_PATH,
        SEQUENCE_LENGTH,
        TARGET_COLUMN,
    )
    from backend.ml.data_pipeline import (
        create_sliding_windows,
        download_dataset,
        fit_and_scale_data,
        load_and_validate_dataset,
        split_chronological,
    )
    from backend.ml.model import build_1d_cnn_bigru_model, get_model_metadata


logger = logging.getLogger("airpurify.ml.train")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate MAE, RMSE, and R2 regression metrics."""
    mae = float(mean_absolute_error(y_true, y_pred))
    mse = float(mean_squared_error(y_true, y_pred))
    rmse = float(np.sqrt(mse))
    r2 = float(r2_score(y_true, y_pred))
    return {
        "mae": round(mae, 3),
        "rmse": round(rmse, 3),
        "r2": round(r2, 4),
        "samples": len(y_true),
    }


def train_and_evaluate(
    epochs: int = EPOCHS,
    batch_size: int = BATCH_SIZE,
    subsample_ratio: float = 1.0,
) -> Tuple[keras.Model, Dict[str, any]]:
    """Execute end-to-end training, validation, baseline benchmarking, and artifact generation."""
    # 1. Acquire dataset
    download_dataset()

    # 2. Ingest & validate
    df, audit = load_and_validate_dataset()
    logger.info("Dataset audit: %s", audit)

    # 3. Chronological split
    train_df, val_df, test_df = split_chronological(df)

    # 4. Fit scaler on train split solely
    scaled_train, scaled_val, scaled_test, feature_scaler, target_scaler = fit_and_scale_data(
        train_df, val_df, test_df, feature_cols=FEATURE_COLUMNS
    )

    # 5. Build sliding windows
    target_idx = FEATURE_COLUMNS.index(TARGET_COLUMN)
    X_train, y_train = create_sliding_windows(scaled_train, target_idx=target_idx)
    X_val, y_val = create_sliding_windows(scaled_val, target_idx=target_idx)
    X_test, y_test = create_sliding_windows(scaled_test, target_idx=target_idx)

    logger.info("Prepared windows: X_train=%s, X_val=%s, X_test=%s", X_train.shape, X_val.shape, X_test.shape)

    # 6. Build model
    n_features = len(FEATURE_COLUMNS)
    model = build_1d_cnn_bigru_model(
        sequence_length=SEQUENCE_LENGTH,
        n_features=n_features,
        learning_rate=LEARNING_RATE,
    )

    # Callbacks
    early_stop = keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=EARLY_STOPPING_PATIENCE,
        restore_best_weights=True,
        verbose=1,
    )

    # 7. Train
    logger.info("Starting model training for up to %d epochs...", epochs)
    history = model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[early_stop],
        verbose=1,
    )

    # 8. Evaluate on test set (unscaled real-world units: ug/m3)
    logger.info("Generating predictions on held-out test set...")
    y_test_pred_scaled = model.predict(X_test, batch_size=batch_size)
    y_test_pred = target_scaler.inverse_transform(y_test_pred_scaled).flatten()
    y_test_actual = target_scaler.inverse_transform(y_test.reshape(-1, 1)).flatten()

    model_metrics = calculate_metrics(y_test_actual, y_test_pred)
    logger.info("Test Set Model Metrics (1D-CNN-BiGRU): %s", model_metrics)

    # 9. Compute baselines
    # Baseline 1: Persistence (last observed PM2.5 in input sequence X_test[:, -1, target_idx])
    persistence_scaled = X_test[:, -1, target_idx].reshape(-1, 1)
    persistence_pred = target_scaler.inverse_transform(persistence_scaled).flatten()
    persistence_metrics = calculate_metrics(y_test_actual, persistence_pred)
    logger.info("Test Set Baseline 1 (Persistence): %s", persistence_metrics)

    # Baseline 2: Historical Mean (predict mean of train set)
    train_pm_mean = float(train_df[TARGET_COLUMN].mean())
    mean_pred = np.full_like(y_test_actual, fill_value=train_pm_mean)
    mean_metrics = calculate_metrics(y_test_actual, mean_pred)
    logger.info("Test Set Baseline 2 (Historical Mean): %s", mean_metrics)

    # 10. Persist Model and Artifacts
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(MODEL_PATH))
    logger.info("Model saved to %s", MODEL_PATH)

    # Build config and evaluation records
    model_config = {
        **get_model_metadata(),
        "feature_columns": FEATURE_COLUMNS,
        "sequence_length": SEQUENCE_LENGTH,
        "forecast_horizon_hours": FORECAST_HORIZON,
        "training_epochs_completed": len(history.history["loss"]),
        "batch_size": batch_size,
        "dataset_provenance": DATASET_PROVENANCE,
        "dataset_audit": audit,
        "train_samples": len(X_train),
        "val_samples": len(X_val),
        "test_samples": len(X_test),
    }

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(model_config, f, indent=2)

    evaluation_report = {
        "model_metrics": model_metrics,
        "baselines": {
            "persistence": persistence_metrics,
            "historical_mean": mean_metrics,
        },
        "target_variable": TARGET_COLUMN,
        "units": "ug/m3",
        "horizon_hours": FORECAST_HORIZON,
        "test_evaluation_timestamp": str(test_df["timestamp"].iloc[SEQUENCE_LENGTH]),
        "performance_relative_to_persistence": {
            "mae_reduction_pct": round(
                (persistence_metrics["mae"] - model_metrics["mae"]) / persistence_metrics["mae"] * 100, 2
            ),
            "rmse_reduction_pct": round(
                (persistence_metrics["rmse"] - model_metrics["rmse"]) / persistence_metrics["rmse"] * 100, 2
            ),
        },
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(evaluation_report, f, indent=2)

    logger.info("Evaluation report saved to %s", REPORT_PATH)
    return model, evaluation_report


if __name__ == "__main__":
    train_and_evaluate()
