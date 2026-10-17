"""Pydantic schemas for request validation and response serialization."""

from datetime import datetime
from typing import Optional, Literal, List
from pydantic import BaseModel, ConfigDict, Field


# -----------------------------------------------------------------------------
# Sensor Reading Schemas
# -----------------------------------------------------------------------------

class ReadingCreate(BaseModel):
    """Schema for incoming ESP32 sensor telemetry."""

    device_id: str = Field(..., min_length=1, max_length=64, description="Unique hardware identifier")
    location_id: str = Field(..., min_length=1, max_length=64, description="Monitored site/room ID")
    timestamp: datetime = Field(..., description="Timestamp captured on edge sensor")
    pm1_0: Optional[float] = Field(None, ge=0.0, le=1000.0, description="PM1.0 concentration in µg/m³")
    pm2_5: float = Field(..., ge=0.0, le=1000.0, description="PM2.5 concentration in µg/m³")
    pm10: float = Field(..., ge=0.0, le=2000.0, description="PM10 concentration in µg/m³")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_id": "ESP32-001",
                "location_id": "Engineering Block",
                "timestamp": "2026-10-16T12:00:00Z",
                "pm1_0": 8.5,
                "pm2_5": 14.2,
                "pm10": 26.8,
            }
        }
    )


class ReadingResponse(BaseModel):
    """Schema for serialized sensor readings returned to clients."""

    id: int
    device_id: str
    location_id: str
    timestamp: datetime
    received_at: datetime
    pm1_0: Optional[float] = None
    pm2_5: float
    pm10: float
    data_quality_status: str

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Device Schemas
# -----------------------------------------------------------------------------

class DeviceCreate(BaseModel):
    """Schema for registering or provisioning a new edge device."""

    device_id: str = Field(..., min_length=1, max_length=64)
    device_name: str = Field(..., min_length=1, max_length=128)
    location_id: str = Field(..., min_length=1, max_length=64)
    firmware_version: Optional[str] = Field(None, max_length=64)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_id": "ESP32-001",
                "device_name": "ESP32 Air Station North",
                "location_id": "Engineering Block",
                "firmware_version": "v1.2.0",
            }
        }
    )


class DeviceResponse(BaseModel):
    """Schema for serialized device records."""

    id: int
    device_id: str
    device_name: str
    location_id: str
    last_seen: Optional[datetime] = None
    status: str
    firmware_version: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Forecast Schemas
# -----------------------------------------------------------------------------

class ForecastResponse(BaseModel):
    """Schema for forecast data points."""

    id: int
    location_id: str
    model_name: str
    model_version: str
    issued_at: datetime
    target_time: datetime
    horizon_hours: int
    predicted_aqi: Optional[float] = None
    predicted_pm25: Optional[float] = None
    predicted_pm10: Optional[float] = None
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class ForecastStatusResponse(BaseModel):
    """Schema for deep learning model engine status."""

    model_name: str
    model_version: str
    status: str
    architecture: str
    is_trained: bool
    message: str
    metrics: Optional[dict] = None
    provenance: Optional[dict] = None
    training_info: Optional[dict] = None


class ForecastPredictRequest(BaseModel):
    """Request schema for on-demand inference."""

    location_id: str
    horizon_hours: int = Field(default=1, ge=1, le=24, description="Forecast horizon in hours")
    recent_pm25_sequence: Optional[List[float]] = Field(
        default=None,
        description="Optional list of up to 24 hourly PM2.5 readings to seed inference",
    )


# -----------------------------------------------------------------------------
# Alert Schemas
# -----------------------------------------------------------------------------

class AlertResponse(BaseModel):
    """Schema for serialized alert records."""

    id: int
    location_id: str
    device_id: str
    alert_type: str
    severity: str
    message: str
    triggered_at: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)


class AlertUpdate(BaseModel):
    """Schema for acknowledging or resolving an alert."""

    status: Literal["acknowledged", "resolved", "active"]


# -----------------------------------------------------------------------------
# Health Check Schema
# -----------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Schema for the health check endpoint."""

    status: str
    app_name: str
    version: str
    database: str
    timestamp: datetime
