"""
Geofence Service
================
Business logic for geofence management and violation detection with MongoDB.

Uses MongoDB geospatial queries:
- $geoWithin: Check if point is inside polygon
- $geoIntersects: Check for intersection
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

from backend.database.connection import get_database
from backend.models.geofence import create_geofence_document, geofence_to_dict, GeofenceType
from backend.api.schemas import GeofenceCreate, GeofenceResponse, CoordinatePoint


class GeofenceService:
    """
    Service class for geofence operations.
    
    Handles geofence CRUD and violation detection using MongoDB geospatial queries.
    """
    
    def __init__(self):
        self.db = get_database()
    
    async def create_geofence(self, geofence_data: GeofenceCreate) -> GeofenceResponse:
        """
        Create a new geofence.
        
        Converts coordinate list to GeoJSON polygon.
        """
        coords = [{"lat": c.lat, "lng": c.lng} for c in geofence_data.coordinates]
        
        doc = create_geofence_document(
            name=geofence_data.name,
            coordinates=coords,
            description=geofence_data.description,
            fence_type=geofence_data.fence_type or GeofenceType.RESTRICTED
        )
        
        result = await self.db.geofences.insert_one(doc)
        doc["_id"] = result.inserted_id
        
        return self._to_response(doc)
    
    async def get_geofence(self, geofence_id: str) -> Optional[GeofenceResponse]:
        """Get a geofence by ID."""
        try:
            geofence = await self.db.geofences.find_one({"_id": ObjectId(geofence_id)})
        except:
            return None
        
        if not geofence:
            return None
        
        return self._to_response(geofence)
    
    async def get_all_geofences(self, active_only: bool = True) -> List[GeofenceResponse]:
        """Get all geofences."""
        query = {}
        if active_only:
            query["is_active"] = True
        
        cursor = self.db.geofences.find(query)
        geofences = await cursor.to_list(length=1000)
        
        return [self._to_response(g) for g in geofences]
    
    async def toggle_geofence(self, geofence_id: str) -> Optional[GeofenceResponse]:
        """Toggle geofence active status."""
        try:
            geofence = await self.db.geofences.find_one({"_id": ObjectId(geofence_id)})
        except:
            return None
        
        if not geofence:
            return None
        
        new_status = not geofence.get("is_active", True)
        
        await self.db.geofences.update_one(
            {"_id": ObjectId(geofence_id)},
            {"$set": {"is_active": new_status, "updated_at": datetime.utcnow()}}
        )
        
        geofence["is_active"] = new_status
        return self._to_response(geofence)
    
    async def delete_geofence(self, geofence_id: str) -> bool:
        """Delete a geofence."""
        try:
            result = await self.db.geofences.delete_one({"_id": ObjectId(geofence_id)})
            return result.deleted_count > 0
        except:
            return False
    
    async def check_point_in_geofences(
        self,
        latitude: float,
        longitude: float
    ) -> List[Dict[str, Any]]:
        """
        Check if a point is inside any active geofence.
        
        Uses MongoDB $geoIntersects for efficient geospatial query.
        
        Args:
            latitude: Point latitude
            longitude: Point longitude
            
        Returns:
            List of geofences that contain the point
        """
        point = {
            "type": "Point",
            "coordinates": [longitude, latitude]
        }
        
        cursor = self.db.geofences.find({
            "is_active": True,
            "geometry": {
                "$geoIntersects": {
                    "$geometry": point
                }
            }
        })
        
        matching = await cursor.to_list(length=100)
        
        violations = []
        for doc in matching:
            violations.append({
                "geofence_id": str(doc["_id"]),
                "name": doc["name"],
                "fence_type": doc["fence_type"],
                "description": doc.get("description")
            })
        
        return violations
    
    def _to_response(self, geofence: dict) -> GeofenceResponse:
        """Convert geofence document to response with coordinates."""
        coordinates = [
            CoordinatePoint(lat=c["lat"], lng=c["lng"])
            for c in geofence.get("coordinates", [])
        ]
        
        return GeofenceResponse(
            id=str(geofence["_id"]),
            name=geofence["name"],
            description=geofence.get("description"),
            fence_type=geofence.get("fence_type", "restricted"),
            is_active=geofence.get("is_active", True),
            coordinates=coordinates,
            created_at=geofence.get("created_at")
        )