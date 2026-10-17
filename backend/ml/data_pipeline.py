"""Data ingestion, validation, preprocessing, and window generation pipeline.

Enforces strictly chronological train/validation/test splits and zero data leakage.
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import urllib.request

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

try:
    from ml.config import (
        DATASET_PATH,
        DATASET_URL,
        FEATURE_COLUMNS,
        FORECAST_HORIZON,
        SCALER_PATH,
        SEQUENCE_LENGTH,
        TARGET_COLUMN,
        TEST_RATIO,
        TRAIN_RATIO,
        VAL_RATIO,
    )
except ImportError:
    from backend.ml.config import (
        DATASET_PATH,
        DATASET_URL,
        FEATURE_COLUMNS,
        FORECAST_HORIZON,
        SCALER_PATH,
        SEQUENCE_LENGTH,
        TARGET_COLUMN,
        TEST_RATIO,
        TRAIN_RATIO,
        VAL_RATIO,
    )


logger = logging.getLogger("airpurify.ml.data_pipeline")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def download_dataset(target_path: Optional[Path] = None, force: bool = False) -> Path:
    """Download the benchmark dataset from UCI Repository if not present."""
    dest = target_path or DATASET_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and not force:
        logger.info("Dataset already exists at %s (%d bytes)", dest, dest.stat().st_size)
        return dest

    logger.info("Downloading dataset from %s ...", DATASET_URL)
    req = urllib.request.Request(DATASET_URL, headers={"User-Agent": "Mozilla/5.0 (AirPurify-AI)"})
    with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as f:
        f.write(resp.read())

    logger.info("Dataset successfully downloaded to %s (%d bytes)", dest, dest.stat().st_size)
    return dest


def load_and_validate_dataset(
    csv_path: Optional[Path] = None,
) -> Tuple[pd.DataFrame, Dict[str, any]]:
    """Load, validate, chronologically sort, and clean the benchmark dataset.

    Returns:
        Tuple of (clean_df, data_audit_report)
    """
    path = csv_path or DATASET_PATH
    if not Path(path).exists():
        raise FileNotFoundError(f"Dataset file not found at {path}. Run download_dataset() first.")

    raw_df = pd.read_csv(path)
    total_raw_rows = len(raw_df)

    # 1. Column verification
    required_raw_cols = ["year", "month", "day", "hour"] + FEATURE_COLUMNS
    for col in required_raw_cols:
        if col not in raw_df.columns:
            raise ValueError(f"Missing required column in dataset: {col}")

    # 2. Parse timestamps & verify chronological order
    raw_df["timestamp"] = pd.to_datetime(
        raw_df[["year", "month", "day", "hour"]].astype(str).agg("-".join, axis=1),
        format="%Y-%m-%d-%H",
    )
    is_initially_sorted = raw_df["timestamp"].is_monotonic_increasing
    if not is_initially_sorted:
        raw_df = raw_df.sort_values("timestamp").reset_index(drop=True)

    # 3. Detect and audit missing values before cleaning
    missing_summary = raw_df[FEATURE_COLUMNS].isna().sum().to_dict()
    missing_pm25 = int(missing_summary.get(TARGET_COLUMN, 0))

    # Check temporal intervals
    time_diffs = raw_df["timestamp"].diff().dropna()
    expected_step = pd.Timedelta(hours=1)
    irregular_intervals = int((time_diffs != expected_step).sum())

    # 4. Handle missing values transparently
    # In the Beijing dataset, initial rows often lack PM2.5 measurements before monitoring began.
    # We drop unmeasured leading entries then forward-fill short gaps up to 3 hours, dropping remainder.
    df = raw_df.copy()
    first_valid_pm_idx = df[TARGET_COLUMN].first_valid_index()
    if first_valid_pm_idx is not None and first_valid_pm_idx > 0:
        df = df.iloc[first_valid_pm_idx:].reset_index(drop=True)

    # Forward fill gaps up to 3 consecutive hours for continuous time-series continuity
    df[FEATURE_COLUMNS] = df[FEATURE_COLUMNS].ffill(limit=3)
    df = df.dropna(subset=[TARGET_COLUMN]).reset_index(drop=True)

    audit_report = {
        "total_raw_records": total_raw_rows,
        "valid_processed_records": len(df),
        "initial_sorted": is_initially_sorted,
        "missing_values_by_column": missing_summary,
        "missing_target_count": missing_pm25,
        "irregular_time_intervals": irregular_intervals,
        "start_timestamp": str(df["timestamp"].min()),
        "end_timestamp": str(df["timestamp"].max()),
    }

    logger.info("Dataset loaded and audited: %d records retained.", len(df))
    return df, audit_report


def split_chronological(
    df: pd.DataFrame,
    train_ratio: float = TRAIN_RATIO,
    val_ratio: float = VAL_RATIO,
    test_ratio: float = TEST_RATIO,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split dataframe into train, validation, and test subsets chronologically.

    No random shuffling is permitted to avoid temporal look-ahead leakage.
    """
    assert abs((train_ratio + val_ratio + test_ratio) - 1.0) < 1e-5, "Ratios must sum to 1.0"

    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    train_df = df.iloc[:train_end].copy().reset_index(drop=True)
    val_df = df.iloc[train_end:val_end].copy().reset_index(drop=True)
    test_df = df.iloc[val_end:].copy().reset_index(drop=True)

    # Verify no temporal overlap
    assert train_df["timestamp"].max() < val_df["timestamp"].min(), "Train overlaps with Val"
    assert val_df["timestamp"].max() < test_df["timestamp"].min(), "Val overlaps with Test"

    logger.info(
        "Chronological split: Train=%d (%s to %s), Val=%d (%s to %s), Test=%d (%s to %s)",
        len(train_df),
        train_df["timestamp"].min(),
        train_df["timestamp"].max(),
        len(val_df),
        val_df["timestamp"].min(),
        val_df["timestamp"].max(),
        len(test_df),
        test_df["timestamp"].min(),
        test_df["timestamp"].max(),
    )
    return train_df, val_df, test_df


def fit_and_scale_data(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_cols: Optional[List[str]] = None,
    save_scaler: bool = True,
    scaler_out_path: Optional[Path] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, MinMaxScaler, MinMaxScaler]:
    """Fit MinMaxScalers on TRAIN data only, then transform val and test data.

    Returns:
        (scaled_train, scaled_val, scaled_test, feature_scaler, target_scaler)
    """
    cols = feature_cols or FEATURE_COLUMNS
    target_idx = cols.index(TARGET_COLUMN)

    # Fit feature scaler solely on training data
    feature_scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_train = feature_scaler.fit_transform(train_df[cols].values)
    scaled_val = feature_scaler.transform(val_df[cols].values)
    scaled_test = feature_scaler.transform(test_df[cols].values)

    # Separate target scaler to allow straightforward inverse transformations
    target_scaler = MinMaxScaler(feature_range=(0, 1))
    target_scaler.fit(train_df[[TARGET_COLUMN]].values)

    if save_scaler:
        out_file = scaler_out_path or SCALER_PATH
        out_file.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "feature_scaler": feature_scaler,
                "target_scaler": target_scaler,
                "feature_cols": cols,
                "target_col": TARGET_COLUMN,
                "target_idx": target_idx,
            },
            out_file,
        )
        logger.info("Scalers successfully persisted to %s", out_file)

    return scaled_train, scaled_val, scaled_test, feature_scaler, target_scaler


def create_sliding_windows(
    data: np.ndarray,
    target_idx: int = 0,
    seq_length: int = SEQUENCE_LENGTH,
    horizon: int = FORECAST_HORIZON,
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate sliding window sequences for multi-input single-output time-series prediction.

    Input shape: (N, seq_length, num_features)
    Target shape: (N,)
    """
    n_samples = len(data) - seq_length - horizon + 1
    if n_samples <= 0:
        raise ValueError(
            f"Data length ({len(data)}) insufficient for sequence_length ({seq_length}) and horizon ({horizon})"
        )

    X = np.empty((n_samples, seq_length, data.shape[1]), dtype=np.float32)
    y = np.empty((n_samples,), dtype=np.float32)

    for i in range(n_samples):
        X[i] = data[i : i + seq_length]
        y[i] = data[i + seq_length + horizon - 1, target_idx]

    return X, y
