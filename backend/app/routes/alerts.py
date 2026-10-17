"""API routes for environmental and device system alerts using MongoDB Atlas."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database

from app.auth import require_admin_auth
from app.database import get_db
from app.models import Alert
from app.schemas import AlertResponse, AlertUpdate

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get(
    "",
    response_model=List[AlertResponse],
    summary="List alerts",
    description="Retrieve system alerts with optional filters for device, location, status, and severity.",
)
def list_alerts(
    device_id: Optional[str] = Query(None, description="Filter by device identifier"),
    location_id: Optional[str] = Query(None, description="Filter by location identifier"),
    alert_status: Optional[str] = Query(None, alias="status", description="Filter by alert status (active, acknowledged, resolved)"),
    severity: Optional[str] = Query(None, description="Filter by severity (info, warning, critical)"),
    limit: int = Query(50, ge=1, le=500, description="Max alerts to retrieve"),
    db: Database = Depends(get_db),
) -> List[Alert]:
    """Retrieve alerts based on filters."""
    query = {}
    if device_id:
        query["device_id"] = device_id
    if location_id:
        query["location_id"] = location_id
    if alert_status:
        query["status"] = alert_status
    if severity:
        query["severity"] = severity

    cursor = db["alerts"].find(query).sort("triggered_at", -1).limit(limit)
    return [Alert.from_mongo(doc) for doc in cursor]


@router.patch(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Update alert status",
    description="Acknowledge or resolve an active alert.",
)
def update_alert_status(
    alert_id: int,
    payload: AlertUpdate,
    db: Database = Depends(get_db),
    _admin: str = Depends(require_admin_auth),
) -> Alert:
    """Update status of a specific alert."""
    doc = db["alerts"].find_one({"id": alert_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {alert_id} was not found.",
        )

    db["alerts"].update_one({"id": alert_id}, {"$set": {"status": payload.status}})
    doc["status"] = payload.status
    return Alert.from_mongo(doc)
