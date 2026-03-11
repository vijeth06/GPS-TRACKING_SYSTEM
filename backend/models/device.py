"""
Device Model
============
MongoDB document schema for GPS tracking devices.
"""

from datetime import datetime
from typing import Optional, Dict, Any
import enum


class DeviceStatus(str, enum.Enum):
    """Device status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class DeviceType(str, enum.Enum):
    """Device type enumeration"""
    VEHICLE = "vehicle"
    PERSON = "person"
    ASSET = "asset"
    DRONE = "drone"


def create_device_document(
    device_id: str,
    device_name: Optional[str] = None,
    device_type: str = DeviceType.VEHICLE.value,
    status: str = DeviceStatus.ACTIVE.value
) -> Dict[str, Any]:
    """
    Create a device document for MongoDB.
    
    Args:
        device_id: Unique device identifier (e.g., TRK101)
        device_name: Human-readable device name
        device_type: Type of device (vehicle, person, asset, drone)
        status: Current device status
        
    Returns:
        Device document dictionary
    """
    now = datetime.utcnow()
    return {
        "device_id": device_id,
        "device_name": device_name or f"Device {device_id}",
        "device_type": device_type,
        "status": status,
        "created_at": now,
        "updated_at": now
    }


def device_to_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB document to API response dictionary"""
    if not doc:
        return None
    return {
        "id": str(doc.get("_id", "")),
        "device_id": doc.get("device_id"),
        "device_name": doc.get("device_name"),
        "device_type": doc.get("device_type"),
        "status": doc.get("status"),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
        "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None
    }
