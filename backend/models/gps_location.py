"""
GPS Location Model
==================
MongoDB document schema for GPS coordinate points with geospatial support.
"""

from datetime import datetime
from typing import Optional, Dict, Any


def create_gps_location_document(
    device_id: str,
    latitude: float,
    longitude: float,
    timestamp: datetime,
    altitude: Optional[float] = None,
    speed: Optional[float] = None,
    heading: Optional[float] = None,
    accuracy: Optional[float] = None
) -> Dict[str, Any]:
    """
    Create a GPS location document for MongoDB.
    
    Uses GeoJSON Point format for geospatial queries with 2dsphere index.
    
    Args:
        device_id: Device identifier
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        timestamp: When the GPS reading was taken
        altitude: Altitude in meters (optional)
        speed: Speed in km/h (optional)
        heading: Direction in degrees from north (optional)
        accuracy: GPS accuracy in meters (optional)
        
    Returns:
        GPS location document dictionary
    """
    return {
        "device_id": device_id,
        "location": {
            "type": "Point",
            "coordinates": [longitude, latitude]
        },
        "latitude": latitude,
        "longitude": longitude,
        "altitude": altitude,
        "speed": speed,
        "heading": heading,
        "accuracy": accuracy,
        "timestamp": timestamp,
        "created_at": datetime.utcnow()
    }


def gps_location_to_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB document to API response dictionary"""
    if not doc:
        return None
    return {
        "id": str(doc.get("_id", "")),
        "device_id": doc.get("device_id"),
        "latitude": doc.get("latitude"),
        "longitude": doc.get("longitude"),
        "altitude": doc.get("altitude"),
        "speed": doc.get("speed"),
        "heading": doc.get("heading"),
        "accuracy": doc.get("accuracy"),
        "timestamp": doc.get("timestamp").isoformat() if doc.get("timestamp") else None,
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None
    }