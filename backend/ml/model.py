"""1D-CNN–BiGRU hybrid neural network architecture for air quality time-series forecasting.

Combines 1D Convolutional layers for local temporal pattern extraction with
Bidirectional GRU layers for long-range bidirectional temporal dependencies.
"""
from pathlib import Path
from typing import Optional, Tuple

import keras
from keras import layers

try:
    from ml.config import (
        ARCHITECTURE_DESCRIPTION,
        LEARNING_RATE,
        MODEL_NAME,
        MODEL_VERSION,
        SEQUENCE_LENGTH,
    )
except ImportError:
    from backend.ml.config import (
        ARCHITECTURE_DESCRIPTION,
        LEARNING_RATE,
        MODEL_NAME,
        MODEL_VERSION,
        SEQUENCE_LENGTH,
    )



def build_1d_cnn_bigru_model(
    sequence_length: int = SEQUENCE_LENGTH,
    n_features: int = 7,
    learning_rate: float = LEARNING_RATE,
) -> keras.Model:
    """Construct and compile the 1D-CNN–BiGRU hybrid model."""
    inputs = layers.Input(shape=(sequence_length, n_features), name="time_series_input")

    # 1. First 1D Convolutional block — extracts local feature patterns
    x = layers.Conv1D(filters=64, kernel_size=3, padding="same", activation="relu", name="conv1d_1")(inputs)
    x = layers.BatchNormalization(name="bn_1")(x)

    # 2. Second 1D Convolutional block — refines representations
    x = layers.Conv1D(filters=32, kernel_size=3, padding="same", activation="relu", name="conv1d_2")(x)
    x = layers.BatchNormalization(name="bn_2")(x)

    # 3. Bidirectional GRU layer — captures forward and backward temporal dynamics
    x = layers.Bidirectional(layers.GRU(64, return_sequences=False), name="bidirectional_gru")(x)

    # 4. Regularization & Dense Projection
    x = layers.Dropout(0.3, name="dropout")(x)
    x = layers.Dense(32, activation="relu", name="dense_latent")(x)
    outputs = layers.Dense(1, activation="linear", name="pm25_output")(x)

    model = keras.Model(inputs=inputs, outputs=outputs, name="AirPurify_1DCNN_BiGRU")

    optimizer = keras.optimizers.Adam(learning_rate=learning_rate)
    model.compile(
        optimizer=optimizer,
        loss="mse",
        metrics=["mae", keras.metrics.RootMeanSquaredError(name="rmse")],
    )

    return model


def get_model_metadata() -> dict:
    """Return model architectural metadata dictionary."""
    return {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "architecture": ARCHITECTURE_DESCRIPTION,
        "input_sequence_length": SEQUENCE_LENGTH,
        "primary_target": "pm2.5",
        "output_dimension": 1,
    }


def load_trained_model(model_path: Path) -> Optional[keras.Model]:
    """Safely load trained model from disk, returning None if missing."""
    if not Path(model_path).exists():
        return None
    return keras.models.load_model(str(model_path))
