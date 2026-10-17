"""Data models for AirPurify AI using MongoDB documents."""

from datetime import datetime, timezone
from typing import Optional, Any, Dict


def utc_now() -> datetime:
    """Return current UTC datetime with timezone information."""
    return datetime.now(timezone.utc)


class BaseModelDocument:
    """Base document class providing attribute and dict-like access."""

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class SensorReading(BaseModelDocument):
    """Stores air quality sensor readings received from edge nodes."""

    def __init__(
        self,
        id: Optional[int] = None,
        device_id: str = "",
        location_id: str = "",
        timestamp: Optional[datetime] = None,
        received_at: Optional[datetime] = None,
        pm1_0: Optional[float] = None,
        pm2_5: float = 0.0,
        pm10: float = 0.0,
        data_quality_status: str = "valid",
        _id: Any = None,
    ):
        self.id = id
        self.device_id = device_id
        self.location_id = location_id
        self.timestamp = timestamp or utc_now()
        self.received_at = received_at or utc_now()
        self.pm1_0 = pm1_0
        self.pm2_5 = float(pm2_5) if pm2_5 is not None else 0.0
        self.pm10 = float(pm10) if pm10 is not None else 0.0
        self.data_quality_status = data_quality_status
        self._mongo_id = _id

    @classmethod
    def from_mongo(cls, doc: Optional[Dict[str, Any]]) -> Optional["SensorReading"]:
        if not doc:
            return None
        return cls(
            id=doc.get("id"),
            device_id=doc.get("device_id", ""),
            location_id=doc.get("location_id", ""),
            timestamp=doc.get("timestamp"),
            received_at=doc.get("received_at"),
            pm1_0=doc.get("pm1_0"),
            pm2_5=doc.get("pm2_5", 0.0),
            pm10=doc.get("pm10", 0.0),
            data_quality_status=doc.get("data_quality_status", "valid"),
            _id=doc.get("_id"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "device_id": self.device_id,
            "location_id": self.location_id,
            "timestamp": self.timestamp,
            "received_at": self.received_at,
            "pm1_0": self.pm1_0,
            "pm2_5": self.pm2_5,
            "pm10": self.pm10,
            "data_quality_status": self.data_quality_status,
        }

    def __repr__(self) -> str:
        return (
            f"<SensorReading(id={self.id}, device='{self.device_id}', "
            f"pm2.5={self.pm2_5}, pm10={self.pm10}, quality='{self.data_quality_status}')>"
        )


class Device(BaseModelDocument):
    """Registered edge sensor devices (e.g. ESP32 stations)."""

    def __init__(
        self,
        id: Optional[int] = None,
        device_id: str = "",
        device_name: str = "",
        location_id: str = "",
        last_seen: Optional[datetime] = None,
        status: str = "active",
        firmware_version: Optional[str] = None,
        _id: Any = None,
    ):
        self.id = id
        self.device_id = device_id
        self.device_name = device_name
        self.location_id = location_id
        self.last_seen = last_seen
        self.status = status
        self.firmware_version = firmware_version
        self._mongo_id = _id

    @classmethod
    def from_mongo(cls, doc: Optional[Dict[str, Any]]) -> Optional["Device"]:
        if not doc:
            return None
        return cls(
            id=doc.get("id"),
            device_id=doc.get("device_id", ""),
            device_name=doc.get("device_name", ""),
            location_id=doc.get("location_id", ""),
            last_seen=doc.get("last_seen"),
            status=doc.get("status", "active"),
            firmware_version=doc.get("firmware_version"),
            _id=doc.get("_id"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "location_id": self.location_id,
            "last_seen": self.last_seen,
            "status": self.status,
            "firmware_version": self.firmware_version,
        }

    def __repr__(self) -> str:
        return f"<Device(id={self.id}, device_id='{self.device_id}', name='{self.device_name}', status='{self.status}')>"


class Forecast(BaseModelDocument):
    """Forecast records produced by deep learning predictive models."""

    def __init__(
        self,
        id: Optional[int] = None,
        location_id: str = "",
        model_name: str = "",
        model_version: str = "",
        issued_at: Optional[datetime] = None,
        target_time: Optional[datetime] = None,
        horizon_hours: int = 1,
        predicted_aqi: Optional[float] = None,
        predicted_pm25: Optional[float] = None,
        predicted_pm10: Optional[float] = None,
        confidence_interval_lower: Optional[float] = None,
        confidence_interval_upper: Optional[float] = None,
        status: str = "model_not_configured",
        _id: Any = None,
    ):
        self.id = id
        self.location_id = location_id
        self.model_name = model_name
        self.model_version = model_version
        self.issued_at = issued_at or utc_now()
        self.target_time = target_time or utc_now()
        self.horizon_hours = horizon_hours
        self.predicted_aqi = predicted_aqi
        self.predicted_pm25 = predicted_pm25
        self.predicted_pm10 = predicted_pm10
        self.confidence_interval_lower = confidence_interval_lower
        self.confidence_interval_upper = confidence_interval_upper
        self.status = status
        self._mongo_id = _id

    @classmethod
    def from_mongo(cls, doc: Optional[Dict[str, Any]]) -> Optional["Forecast"]:
        if not doc:
            return None
        return cls(
            id=doc.get("id"),
            location_id=doc.get("location_id", ""),
            model_name=doc.get("model_name", ""),
            model_version=doc.get("model_version", ""),
            issued_at=doc.get("issued_at"),
            target_time=doc.get("target_time"),
            horizon_hours=doc.get("horizon_hours", 1),
            predicted_aqi=doc.get("predicted_aqi"),
            predicted_pm25=doc.get("predicted_pm25"),
            predicted_pm10=doc.get("predicted_pm10"),
            confidence_interval_lower=doc.get("confidence_interval_lower"),
            confidence_interval_upper=doc.get("confidence_interval_upper"),
            status=doc.get("status", "model_not_configured"),
            _id=doc.get("_id"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "location_id": self.location_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "issued_at": self.issued_at,
            "target_time": self.target_time,
            "horizon_hours": self.horizon_hours,
            "predicted_aqi": self.predicted_aqi,
            "predicted_pm25": self.predicted_pm25,
            "predicted_pm10": self.predicted_pm10,
            "confidence_interval_lower": self.confidence_interval_lower,
            "confidence_interval_upper": self.confidence_interval_upper,
            "status": self.status,
        }

    def __repr__(self) -> str:
        return (
            f"<Forecast(id={self.id}, location='{self.location_id}', "
            f"target='{self.target_time}', aqi={self.predicted_aqi}, status='{self.status}')>"
        )


class Alert(BaseModelDocument):
    """System and environmental alerts."""

    def __init__(
        self,
        id: Optional[int] = None,
        location_id: str = "",
        device_id: str = "",
        alert_type: str = "",
        severity: str = "warning",
        message: str = "",
        triggered_at: Optional[datetime] = None,
        status: str = "active",
        _id: Any = None,
    ):
        self.id = id
        self.location_id = location_id
        self.device_id = device_id
        self.alert_type = alert_type
        self.severity = severity
        self.message = message
        self.triggered_at = triggered_at or utc_now()
        self.status = status
        self._mongo_id = _id

    @classmethod
    def from_mongo(cls, doc: Optional[Dict[str, Any]]) -> Optional["Alert"]:
        if not doc:
            return None
        return cls(
            id=doc.get("id"),
            location_id=doc.get("location_id", ""),
            device_id=doc.get("device_id", ""),
            alert_type=doc.get("alert_type", ""),
            severity=doc.get("severity", "warning"),
            message=doc.get("message", ""),
            triggered_at=doc.get("triggered_at"),
            status=doc.get("status", "active"),
            _id=doc.get("_id"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "location_id": self.location_id,
            "device_id": self.device_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "triggered_at": self.triggered_at,
            "status": self.status,
        }

    def __repr__(self) -> str:
        return (
            f"<Alert(id={self.id}, device='{self.device_id}', "
            f"type='{self.alert_type}', severity='{self.severity}', status='{self.status}')>"
        )
