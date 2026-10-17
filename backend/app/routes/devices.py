"""API routes for managing edge sensor devices using MongoDB Atlas."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database

from app.auth import require_admin_auth
from app.database import get_db, get_next_sequence_value
from app.models import Device
from app.schemas import DeviceCreate, DeviceResponse
from app.services.alerts import evaluate_device_health

router = APIRouter(prefix="/api/devices", tags=["Devices"])


@router.get(
    "",
    response_model=List[DeviceResponse],
    summary="List registered devices",
    description="Retrieve all registered edge sensor devices.",
)
def list_devices(
    location_id: Optional[str] = Query(None, description="Filter by location identifier"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (active, offline)"),
    db: Database = Depends(get_db),
) -> List[Device]:
    """List devices with optional filters."""
    query = {}
    if location_id:
        query["location_id"] = location_id
    if status_filter:
        query["status"] = status_filter

    devices = [Device.from_mongo(doc) for doc in db["devices"].find(query)]
    # Evaluate liveness for devices
    for dev in devices:
        evaluate_device_health(db, dev)

    return devices


@router.post(
    "",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new device",
    description="Manually provision or register an edge sensor node.",
)
def register_device(
    payload: DeviceCreate,
    db: Database = Depends(get_db),
    _admin: str = Depends(require_admin_auth),
) -> Device:
    """Register a new device."""
    existing = db["devices"].find_one({"device_id": payload.device_id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device with ID '{payload.device_id}' is already registered.",
        )

    dev_seq = get_next_sequence_value(db, "devices_id")
    doc = {
        "id": dev_seq,
        "device_id": payload.device_id,
        "device_name": payload.device_name,
        "location_id": payload.location_id,
        "firmware_version": payload.firmware_version,
        "status": "active",
        "last_seen": None,
    }
    db["devices"].insert_one(doc)
    return Device.from_mongo(doc)


@router.get(
    "/{device_id}",
    response_model=DeviceResponse,
    summary="Get device by identifier",
    description="Retrieve details for a specific device by its hardware ID.",
)
def get_device(
    device_id: str,
    db: Database = Depends(get_db),
) -> Device:
    """Retrieve details of a single device."""
    doc = db["devices"].find_one({"device_id": device_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' was not found.",
        )

    device = Device.from_mongo(doc)
    evaluate_device_health(db, device)
    return device
