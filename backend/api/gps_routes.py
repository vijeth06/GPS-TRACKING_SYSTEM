"""
GPS Routes
==========
API endpoints for GPS data operations.

Endpoints:
    POST /gps - Receive GPS data from devices
    GET /devices - List all devices
    GET /device/{id}/trail - Get device movement history
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime, timedelta
from typing import List, Optional

from backend.api.schemas import (
    GPSDataInput,
    GPSDataResponse,
    DeviceDeleteResponse,
    DeviceWithLocation,
    DeviceTrailResponse,
    DeviceOnboardRequest,
    DeviceCredentialResponse,
    DeviceCredentialStatusResponse,
    DeviceResponse,
    DeviceUpdateRequest,
)
from backend.services.auth_dependencies import require_roles
from backend.services.auth_service import UserRole
from backend.services.gps_service import GPSService
from backend.services.device_service import DeviceService

router = APIRouter(tags=["GPS"])


@router.post("/gps", response_model=dict, summary="Receive GPS data")
async def receive_gps_data(gps_data: GPSDataInput):
    """
    Receive GPS location data from a device.
    
    This endpoint:
    1. Creates the device if it doesn't exist
    2. Stores the GPS location point
    3. Triggers movement analysis
    4. Checks for geofence violations
    5. Broadcasts real-time update via WebSocket
    
    Args:
        gps_data: GPS location payload from device
        
    Returns:
        Success status and any generated alerts
    """
    gps_service = GPSService()
    result = await gps_service.process_gps_data(gps_data)
    return result


@router.get("/devices", response_model=List[DeviceWithLocation], summary="List all devices")
async def get_all_devices(
    status: Optional[str] = Query(None, description="Filter by status")
):
    """
    Get a list of all registered devices with their latest locations.
    
    Args:
        status: Optional filter by device status (active, inactive)
        
    Returns:
        List of devices with latest location and basic analytics
    """
    device_service = DeviceService()
    devices = await device_service.get_all_devices_with_locations(status_filter=status)
    return devices


@router.get("/device/{device_id}", response_model=DeviceWithLocation, summary="Get device details")
async def get_device(device_id: str):
    """
    Get details for a specific device including latest location.
    
    Args:
        device_id: Unique device identifier
        
    Returns:
        Device details with latest location
    """
    device_service = DeviceService()
    device = await device_service.get_device_with_location(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    return device


@router.put(
    "/devices/{device_id}",
    response_model=DeviceResponse,
    summary="Update managed device",
)
async def update_device(
    device_id: str,
    payload: DeviceUpdateRequest,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
):
    _ = current_user
    device_service = DeviceService()
    updated = await device_service.update_device(
        device_id=device_id,
        device_name=payload.device_name,
        device_type=payload.device_type,
        status=payload.status,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    return DeviceResponse(
        id=str(updated["_id"]),
        device_id=updated["device_id"],
        device_name=updated.get("device_name"),
        device_type=updated.get("device_type", "vehicle"),
        status=updated.get("status", "active"),
        created_at=updated.get("created_at"),
        updated_at=updated.get("updated_at"),
    )


@router.delete(
    "/devices/{device_id}",
    response_model=DeviceDeleteResponse,
    summary="Delete managed device",
)
async def delete_device(
    device_id: str,
    current_user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    _ = current_user
    device_service = DeviceService()
    result = await device_service.delete_device(device_id)
    if not result.get("deleted"):
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    return DeviceDeleteResponse(**result)


@router.post(
    "/devices/onboard",
    response_model=DeviceCredentialResponse,
    summary="Onboard device and issue API key",
)
async def onboard_device(
    payload: DeviceOnboardRequest,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
):
    """Provision device credentials and return API key once."""
    _ = current_user
    device_service = DeviceService()
    result = await device_service.onboard_device(
        device_id=payload.device_id,
        device_name=payload.device_name,
        device_type=payload.device_type or "vehicle",
    )
    return DeviceCredentialResponse(**result)


@router.post(
    "/devices/{device_id}/credentials/rotate",
    response_model=DeviceCredentialResponse,
    summary="Rotate device API key",
)
async def rotate_device_credential(
    device_id: str,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
):
    """Rotate a device API key and return new key once."""
    _ = current_user
    device_service = DeviceService()
    try:
        result = await device_service.rotate_device_api_key(device_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return DeviceCredentialResponse(**result)


@router.get(
    "/devices/{device_id}/credentials/status",
    response_model=DeviceCredentialStatusResponse,
    summary="Get device credential status",
)
async def get_device_credential_status(
    device_id: str,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER])),
):
    """Return whether the device has active credentials without exposing secrets."""
    _ = current_user
    device_service = DeviceService()
    status = await device_service.get_device_credential_status(device_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    return DeviceCredentialStatusResponse(**status)


@router.get("/device/{device_id}/trail", response_model=DeviceTrailResponse, summary="Get device trail")
async def get_device_trail(
    device_id: str,
    start_time: Optional[datetime] = Query(None, description="Start of time range"),
    end_time: Optional[datetime] = Query(None, description="End of time range"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum points to return")
):
    """
    Get the movement trail/history for a device.
    
    Returns a list of GPS points forming the device's path, which can
    be visualized as a polyline on the map.
    
    Args:
        device_id: Unique device identifier
        start_time: Optional start of time range (default: last 24 hours)
        end_time: Optional end of time range (default: now)
        limit: Maximum number of points to return
        
    Returns:
        Trail data including points and total distance
    """
    if not end_time:
        end_time = datetime.utcnow()
    if not start_time:
        start_time = end_time - timedelta(hours=24)
    
    gps_service = GPSService()
    trail = await gps_service.get_device_trail(device_id, start_time, end_time, limit)
    
    if trail is None:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    return trail


@router.get("/device/{device_id}/locations", response_model=List[GPSDataResponse], summary="Get raw locations")
async def get_device_locations(
    device_id: str,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get raw GPS location records for a device.
    
    Args:
        device_id: Unique device identifier
        start_time: Optional start of time range
        end_time: Optional end of time range
        limit: Maximum records to return
        
    Returns:
        List of GPS location records
    """
    gps_service = GPSService()
    locations = await gps_service.get_device_locations(device_id, start_time, end_time, limit)
    return locations