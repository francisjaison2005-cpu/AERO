"""ML Pipeline Configuration & Metadata.

Defines model architecture parameters, feature specifications, and dataset provenance.
"""
import os
from pathlib import Path

# Base directories
ML_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("ML_DATA_DIR")).resolve() if os.getenv("ML_DATA_DIR") else ML_DIR / "data"
ARTIFACTS_DIR = (
    Path(os.getenv("ML_ARTIFACTS_DIR")).resolve()
    if os.getenv("ML_ARTIFACTS_DIR")
    else ML_DIR / "artifacts"
)

DATA_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

# Dataset Provenance
DATASET_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/00381/PRSA_data_2010.1.1-2014.12.31.csv"
DATASET_FILENAME = "beijing_pm25.csv"
DATASET_PATH = DATA_DIR / DATASET_FILENAME
DATASET_PROVENANCE = {
    "source_name": "UCI Machine Learning Repository — Beijing PM2.5 Dataset",
    "citation": "Liang, X., Zou, T., Guo, B., Li, S., Zhang, X., Zhang, S., Huang, H. and Chen, S.X. (2015). Assessing Beijing's PM2.5 pollution: severity, weather impact, APEC and numerical model predictions. Atmospheric Environment, 111, 40-52.",
    "time_range": "2010-01-01 00:00 to 2014-12-31 23:00 (Hourly, 43,824 records)",
    "target_pollutant": "PM2.5 (ug/m3)",
    "sensor_type_disclaimer": "Trained on historical meteorological & air quality station records for pipeline validation. Physical PMS5003 sensor fine-tuning is scheduled for Phase 5.",
}

# Features configuration
# Meteorological features + target PM2.5
TARGET_COLUMN = "pm2.5"
FEATURE_COLUMNS = [
    "pm2.5",
    "DEWP",  # Dew point (deg C)
    "TEMP",  # Temperature (deg C)
    "PRES",  # Pressure (hPa)
    "Iws",   # Cumulated wind speed (m/s)
    "Is",    # Cumulated hours of snow
    "Ir",    # Cumulated hours of rain
]

# Time series parameters
SEQUENCE_LENGTH = 24  # 24-hour lookback window
FORECAST_HORIZON = 1  # 1-hour ahead prediction
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# Model architecture & training settings
MODEL_NAME = "AirPurify 1D-CNN-BiGRU"
MODEL_VERSION = "v1.0-hybrid"
ARCHITECTURE_DESCRIPTION = (
    "1D-CNN (64 & 32 filters, kernel 3) + BatchNorm + Bidirectional GRU (64 units) "
    "+ Dropout (0.3) + Dense (32) + Output (1)"
)

BATCH_SIZE = 64
EPOCHS = 20
LEARNING_RATE = 0.001
EARLY_STOPPING_PATIENCE = 4

# Artifact paths
MODEL_PATH = ARTIFACTS_DIR / "model.keras"
SCALER_PATH = ARTIFACTS_DIR / "scaler.joblib"
CONFIG_PATH = ARTIFACTS_DIR / "model_config.json"
REPORT_PATH = ARTIFACTS_DIR / "evaluation_report.json"
