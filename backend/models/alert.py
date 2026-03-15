"""
Alert Model
===========
MongoDB document schema for system alerts and notifications.
"""

from datetime import datetime
from typing import Optional, Dict, Any


class AlertType:
    """Alert type constants"""
    STATIONARY = "stationary_alert"  # Device stopped too long
    SPEED = "speed_alert"  # Speed threshold exceeded
    GEOFENCE = "geofence_alert"  # Geofence violation
    OFFLINE = "offline_alert"  # Device went offline
    BATTERY = "battery_alert"  # Low battery warning


class AlertSeverity:
    """Alert severity constants"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def create_alert_document(
    device_id: str,
    alert_type: str,
    message: str,
    severity: str = AlertSeverity.MEDIUM,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create an alert document for MongoDB.
    
    Args:
        device_id: Device that triggered the alert
        alert_type: Type of alert (stationary, speed, geofence)
        message: Human-readable alert message
        severity: Alert severity level
        latitude: Location where alert was triggered
        longitude: Location where alert was triggered
        metadata: Additional alert-specific data
        
    Returns:
        Alert document dictionary
    """
    now = datetime.utcnow()
    doc = {
        "device_id": device_id,
        "alert_type": alert_type,
        "severity": severity,
        "message": message,
        "latitude": latitude,
        "longitude": longitude,
        "metadata": metadata,
        "status": "triggered",
        "is_acknowledged": False,
        "acknowledged_at": None,
        "resolved_at": None,
        "assigned_to": None,
        "assigned_by": None,
        "assigned_at": None,
        "escalation_level": 0,
        "escalated_at": None,
        "escalation_due_at": now,
        "timestamp": now,
        "created_at": now
    }
    
    if latitude is not None and longitude is not None:
        doc["location"] = {
            "type": "Point",
            "coordinates": [longitude, latitude]
        }
    
    return doc


def alert_to_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB document to API response dictionary"""
    if not doc:
        return None
    return {
        "id": str(doc.get("_id", "")),
        "device_id": doc.get("device_id"),
        "alert_type": doc.get("alert_type"),
        "severity": doc.get("severity"),
        "message": doc.get("message"),
        "latitude": doc.get("latitude"),
        "longitude": doc.get("longitude"),
        "metadata": doc.get("metadata"),
        "status": doc.get("status", "triggered"),
        "is_acknowledged": doc.get("is_acknowledged", False),
        "acknowledged_at": doc.get("acknowledged_at").isoformat() if doc.get("acknowledged_at") else None,
        "resolved_at": doc.get("resolved_at").isoformat() if doc.get("resolved_at") else None,
        "assigned_to": doc.get("assigned_to"),
        "assigned_at": doc.get("assigned_at").isoformat() if doc.get("assigned_at") else None,
        "assigned_by": doc.get("assigned_by"),
        "escalation_level": doc.get("escalation_level", 0),
        "escalated_at": doc.get("escalated_at").isoformat() if doc.get("escalated_at") else None,
        "escalation_due_at": doc.get("escalation_due_at").isoformat() if doc.get("escalation_due_at") else None,
        "timestamp": doc.get("timestamp").isoformat() if doc.get("timestamp") else None,
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None
    }