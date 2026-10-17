"""Alert evaluation service for thresholds, stale data, and device health using MongoDB Atlas."""

import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from pymongo.database import Database
from app.database import get_next_sequence_value
from app.models import Alert, Device, SensorReading

# Configurable default thresholds
PM25_WARNING = float(os.getenv("PM25_WARNING_THRESHOLD", "35.0"))
PM25_CRITICAL = float(os.getenv("PM25_CRITICAL_THRESHOLD", "55.0"))
PM10_WARNING = float(os.getenv("PM10_WARNING_THRESHOLD", "54.0"))
PM10_CRITICAL = float(os.getenv("PM10_CRITICAL_THRESHOLD", "154.0"))
STALE_THRESHOLD_MINUTES = int(os.getenv("STALE_DATA_THRESHOLD_MINUTES", "15"))


def get_active_alert(
    db: Database,
    device_id: str,
    alert_type: str,
) -> Optional[Alert]:
    """Retrieve any existing active alert for the specified device and alert type."""
    doc = db["alerts"].find_one({
        "device_id": device_id,
        "alert_type": alert_type,
        "status": "active",
    })
    return Alert.from_mongo(doc)


def create_alert_if_not_duplicate(
    db: Database,
    device_id: str,
    location_id: str,
    alert_type: str,
    severity: str,
    message: str,
) -> Optional[Alert]:
    """Create a new alert only if an identical active alert does not already exist."""
    existing = get_active_alert(db, device_id, alert_type)
    now = datetime.now(timezone.utc)
    if existing:
        # If severity escalated, update the existing active alert rather than duplicating
        if severity == "critical" and existing.severity != "critical":
            db["alerts"].update_one(
                {"id": existing.id},
                {"$set": {"severity": "critical", "message": message, "triggered_at": now}},
            )
            existing.severity = "critical"
            existing.message = message
            existing.triggered_at = now
            return existing
        return None

    new_id = get_next_sequence_value(db, "alerts_id")
    doc = {
        "id": new_id,
        "device_id": device_id,
        "location_id": location_id,
        "alert_type": alert_type,
        "severity": severity,
        "message": message,
        "triggered_at": now,
        "status": "active",
    }
    db["alerts"].insert_one(doc)
    return Alert.from_mongo(doc)


def evaluate_reading_alerts(db: Database, reading: SensorReading) -> List[Alert]:
    """Evaluate a newly ingested sensor reading against defined environmental thresholds."""
    generated_alerts: List[Alert] = []

    # 1. PM2.5 evaluation
    if reading.pm2_5 is not None:
        if reading.pm2_5 >= PM25_CRITICAL:
            alert = create_alert_if_not_duplicate(
                db=db,
                device_id=reading.device_id,
                location_id=reading.location_id,
                alert_type="HIGH_PM25",
                severity="critical",
                message=(
                    f"CRITICAL: PM2.5 concentration at {reading.location_id} reached "
                    f"{reading.pm2_5} µg/m³ (exceeds critical threshold {PM25_CRITICAL} µg/m³)."
                ),
            )
            if alert:
                generated_alerts.append(alert)
        elif reading.pm2_5 >= PM25_WARNING:
            alert = create_alert_if_not_duplicate(
                db=db,
                device_id=reading.device_id,
                location_id=reading.location_id,
                alert_type="HIGH_PM25",
                severity="warning",
                message=(
                    f"WARNING: PM2.5 concentration at {reading.location_id} reached "
                    f"{reading.pm2_5} µg/m³ (exceeds warning threshold {PM25_WARNING} µg/m³)."
                ),
            )
            if alert:
                generated_alerts.append(alert)

    # 2. PM10 evaluation
    if reading.pm10 is not None:
        if reading.pm10 >= PM10_CRITICAL:
            alert = create_alert_if_not_duplicate(
                db=db,
                device_id=reading.device_id,
                location_id=reading.location_id,
                alert_type="HIGH_PM10",
                severity="critical",
                message=(
                    f"CRITICAL: PM10 concentration at {reading.location_id} reached "
                    f"{reading.pm10} µg/m³ (exceeds critical threshold {PM10_CRITICAL} µg/m³)."
                ),
            )
            if alert:
                generated_alerts.append(alert)
        elif reading.pm10 >= PM10_WARNING:
            alert = create_alert_if_not_duplicate(
                db=db,
                device_id=reading.device_id,
                location_id=reading.location_id,
                alert_type="HIGH_PM10",
                severity="warning",
                message=(
                    f"WARNING: PM10 concentration at {reading.location_id} reached "
                    f"{reading.pm10} µg/m³ (exceeds warning threshold {PM10_WARNING} µg/m³)."
                ),
            )
            if alert:
                generated_alerts.append(alert)

    return generated_alerts


def evaluate_device_health(
    db: Database,
    device: Device,
    stale_minutes: int = STALE_THRESHOLD_MINUTES,
) -> Optional[Alert]:
    """Check if a device has gone stale or stopped communicating."""
    if not device.last_seen:
        return None

    now = datetime.now(timezone.utc)
    last_seen = device.last_seen
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)

    delta = now - last_seen
    if delta > timedelta(minutes=stale_minutes):
        device.status = "offline"
        db["devices"].update_one(
            {"device_id": device.device_id},
            {"$set": {"status": "offline"}},
        )

        return create_alert_if_not_duplicate(
            db=db,
            device_id=device.device_id,
            location_id=device.location_id,
            alert_type="DEVICE_OFFLINE",
            severity="warning",
            message=(
                f"Communication lost for device '{device.device_id}' at '{device.location_id}'. "
                f"No telemetry received for {int(delta.total_seconds() / 60)} minutes."
            ),
        )

    # If device was offline but now has recent telemetry, mark active
    if device.status == "offline":
        device.status = "active"
        db["devices"].update_one(
            {"device_id": device.device_id},
            {"$set": {"status": "active"}},
        )

    return None
