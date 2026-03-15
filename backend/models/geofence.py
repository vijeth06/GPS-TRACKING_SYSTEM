"""
Geofence Model
==============
MongoDB document schema for geofence polygons with geospatial support.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional


class GeofenceType:
    """Geofence type constants"""
    RESTRICTED = "restricted"  # No entry allowed
    ALLOWED = "allowed"  # Safe zone
    WARNING = "warning"  # Warning zone (e.g., school areas)


def create_geofence_document(
    name: str,
    coordinates: List[Dict[str, float]],
    description: Optional[str] = None,
    fence_type: str = GeofenceType.RESTRICTED,
    is_active: bool = True
) -> Dict[str, Any]:
    """
    Create a geofence document for MongoDB.
    
    Uses GeoJSON Polygon format for geospatial queries with 2dsphere index.
    
    Args:
        name: Geofence name
        coordinates: List of {lat, lng} dictionaries forming a polygon
        description: Detailed description
        fence_type: Type of geofence (restricted, allowed, warning)
        is_active: Whether the geofence is currently active
        
    Returns:
        Geofence document dictionary
    """
    geojson_coords = [[coord["lng"], coord["lat"]] for coord in coordinates]
    if geojson_coords[0] != geojson_coords[-1]:
        geojson_coords.append(geojson_coords[0])
    
    now = datetime.utcnow()
    return {
        "name": name,
        "description": description,
        "geometry": {
            "type": "Polygon",
            "coordinates": [geojson_coords]  # Array of linear rings
        },
        "coordinates": coordinates,
        "fence_type": fence_type,
        "is_active": is_active,
        "created_at": now,
        "updated_at": now
    }


def geofence_to_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB document to API response dictionary"""
    if not doc:
        return None
    return {
        "id": str(doc.get("_id", "")),
        "name": doc.get("name"),
        "description": doc.get("description"),
        "fence_type": doc.get("fence_type"),
        "is_active": doc.get("is_active"),
        "coordinates": doc.get("coordinates", []),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
        "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None
    }