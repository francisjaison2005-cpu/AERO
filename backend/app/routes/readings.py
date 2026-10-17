"""API routes for ingesting and querying sensor readings using MongoDB Atlas."""

import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database

from app.auth import require_device_auth
from app.database import get_db, get_next_sequence_value
from app.models import SensorReading, Device
from app.rate_limiter import rate_limit, ingestion_rate_limiter
from app.schemas import ReadingCreate, ReadingResponse
from app.services.alerts import evaluate_reading_alerts

logger = logging.getLogger("airpurify.readings")
router = APIRouter(prefix="/api/readings", tags=["Sensor Readings"])


def assess_reading_quality(payload: ReadingCreate) -> str:
    """Assess physical realism of telemetry values."""
    if payload.pm2_5 < 0 or payload.pm2_5 > 1000 or payload.pm10 < 0 or payload.pm10 > 2000:
        return "out_of_range"
    if payload.pm1_0 is not None and payload.pm1_0 > (payload.pm2_5 * 1.5):
        # Physical anomaly: PM1.0 significantly exceeds PM2.5
        return "questionable"
    return "valid"


@router.post(
    "",
    response_model=ReadingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest ESP32 sensor reading",
    description="Receives particulate telemetry (PM1.0, PM2.5, PM10) from edge sensor nodes.",
)
def ingest_reading(
    payload: ReadingCreate,
    db: Database = Depends(get_db),
    _auth_client: str = Depends(require_device_auth),
    _rate_check: None = Depends(rate_limit(ingestion_rate_limiter)),
) -> SensorReading:
    """Ingest new sensor reading from ESP32."""
    try:
        quality_status = assess_reading_quality(payload)

        reading_time = payload.timestamp
        if reading_time.tzinfo is None:
            reading_time = reading_time.replace(tzinfo=timezone.utc)

        # 1. Ensure device record exists and update last_seen
        device_doc = db["devices"].find_one({"device_id": payload.device_id})
        if not device_doc:
            dev_id_seq = get_next_sequence_value(db, "devices_id")
            db["devices"].insert_one({
                "id": dev_id_seq,
                "device_id": payload.device_id,
                "device_name": f"Sensor Node {payload.device_id}",
                "location_id": payload.location_id,
                "last_seen": reading_time,
                "status": "active",
                "firmware_version": None,
            })
        else:
            db["devices"].update_one(
                {"device_id": payload.device_id},
                {"$set": {
                    "last_seen": reading_time,
                    "location_id": payload.location_id,
                    "status": "active",
                }},
            )

        # 2. Persist sensor reading
        reading_seq = get_next_sequence_value(db, "readings_id")
        now_utc = datetime.now(timezone.utc)
        reading_doc = {
            "id": reading_seq,
            "device_id": payload.device_id,
            "location_id": payload.location_id,
            "timestamp": reading_time,
            "received_at": now_utc,
            "pm1_0": payload.pm1_0,
            "pm2_5": payload.pm2_5,
            "pm10": payload.pm10,
            "data_quality_status": quality_status,
        }
        db["sensor_readings"].insert_one(reading_doc)
        new_reading = SensorReading.from_mongo(reading_doc)

        # 3. Evaluate environmental threshold alerts
        evaluate_reading_alerts(db, new_reading)

        return new_reading

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Internal error while recording telemetry: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record sensor telemetry.",
        )


@router.get(
    "/latest",
    response_model=ReadingResponse,
    summary="Get latest sensor reading",
    description="Retrieve the most recent reading, optionally filtered by device or location.",
)
def get_latest_reading(
    device_id: Optional[str] = Query(None, description="Filter by device identifier"),
    location_id: Optional[str] = Query(None, description="Filter by location identifier"),
    db: Database = Depends(get_db),
) -> SensorReading:
    """Retrieve the single latest sensor reading."""
    query = {}
    if device_id:
        query["device_id"] = device_id
    if location_id:
        query["location_id"] = location_id

    doc = db["sensor_readings"].find_one(query, sort=[("timestamp", -1)])
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No sensor readings found matching the provided criteria.",
        )

    return SensorReading.from_mongo(doc)


@router.get(
    "/history",
    response_model=List[ReadingResponse],
    summary="Get sensor reading history",
    description="Retrieve historical sensor data with optional time range and pagination.",
)
def get_reading_history(
    device_id: Optional[str] = Query(None, description="Filter by device identifier"),
    location_id: Optional[str] = Query(None, description="Filter by location identifier"),
    start_time: Optional[datetime] = Query(None, description="Start time filter (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time filter (ISO format)"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Database = Depends(get_db),
) -> List[SensorReading]:
    """Retrieve historical telemetry records."""
    query = {}
    if device_id:
        query["device_id"] = device_id
    if location_id:
        query["location_id"] = location_id
    if start_time or end_time:
        time_query = {}
        if start_time:
            time_query["$gte"] = start_time
        if end_time:
            time_query["$lte"] = end_time
        query["timestamp"] = time_query

    cursor = db["sensor_readings"].find(query).sort("timestamp", -1).skip(offset).limit(limit)
    return [SensorReading.from_mongo(doc) for doc in cursor]
