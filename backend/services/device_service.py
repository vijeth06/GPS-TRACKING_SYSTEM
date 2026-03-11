"""
Device Service
==============
Business logic for device management with MongoDB.
"""

from typing import Optional, List
from datetime import datetime, timedelta
from bson import ObjectId

from backend.database.connection import get_database
from backend.models.device import DeviceStatus, create_device_document
from backend.api.schemas import DeviceResponse, DeviceWithLocation, GPSDataResponse


class DeviceService:
    """
    Service class for device operations.
    
    Handles device registration, lookup, and status management.
    """
    
    def __init__(self):
        self.db = get_database()
    
    async def get_device(self, device_id: str) -> Optional[dict]:
        """Get a device by its ID."""
        return await self.db.devices.find_one({"device_id": device_id})
    
    async def get_or_create_device(
        self,
        device_id: str,
        device_name: Optional[str] = None,
        device_type: str = "vehicle"
    ) -> dict:
        """
        Get existing device or create new one.
        
        This is called automatically when GPS data arrives for a new device.
        """
        device = await self.get_device(device_id)
        
        if not device:
            doc = create_device_document(
                device_id=device_id,
                device_name=device_name,
                device_type=device_type,
                status=DeviceStatus.ACTIVE.value
            )
            result = await self.db.devices.insert_one(doc)
            doc["_id"] = result.inserted_id
            device = doc
        
        return device
    
    async def get_all_devices(self, status_filter: Optional[str] = None) -> List[dict]:
        """Get all devices with optional status filter."""
        query = {}
        if status_filter:
            query["status"] = status_filter
        
        cursor = self.db.devices.find(query).sort("device_id", 1)
        return await cursor.to_list(length=1000)
    
    async def get_device_with_location(self, device_id: str) -> Optional[DeviceWithLocation]:
        """Get device with its latest location."""
        device = await self.get_device(device_id)
        if not device:
            return None
        
        # Get latest location
        latest_location = await self.db.gps_locations.find_one(
            {"device_id": device_id},
            sort=[("timestamp", -1)]
        )
        
        # Calculate basic analytics
        total_distance, avg_speed = await self._calculate_device_stats(device_id)
        
        location_response = None
        if latest_location:
            location_response = GPSDataResponse(
                id=str(latest_location["_id"]),
                device_id=latest_location["device_id"],
                latitude=latest_location["latitude"],
                longitude=latest_location["longitude"],
                altitude=latest_location.get("altitude"),
                speed=latest_location.get("speed"),
                heading=latest_location.get("heading"),
                accuracy=latest_location.get("accuracy"),
                timestamp=latest_location["timestamp"],
                created_at=latest_location["created_at"]
            )
        
        return DeviceWithLocation(
            id=str(device["_id"]),
            device_id=device["device_id"],
            device_name=device.get("device_name"),
            device_type=device.get("device_type", "vehicle"),
            status=device.get("status", "active"),
            created_at=device.get("created_at"),
            updated_at=device.get("updated_at"),
            latest_location=location_response,
            total_distance=total_distance,
            average_speed=avg_speed
        )
    
    async def get_all_devices_with_locations(
        self,
        status_filter: Optional[str] = None
    ) -> List[DeviceWithLocation]:
        """Get all devices with their latest locations."""
        devices = await self.get_all_devices(status_filter)
        result = []
        
        for device in devices:
            device_with_loc = await self.get_device_with_location(device["device_id"])
            if device_with_loc:
                result.append(device_with_loc)
        
        return result
    
    async def _calculate_device_stats(self, device_id: str) -> tuple:
        """Calculate basic statistics for a device (last 24 hours)."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        
        # Aggregation pipeline for average speed
        pipeline = [
            {
                "$match": {
                    "device_id": device_id,
                    "timestamp": {"$gte": start_time},
                    "speed": {"$ne": None}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "avg_speed": {"$avg": "$speed"}
                }
            }
        ]
        
        result = await self.db.gps_locations.aggregate(pipeline).to_list(length=1)
        avg_speed = round(result[0]["avg_speed"], 2) if result and result[0].get("avg_speed") else 0
        
        # Total distance is calculated separately
        total_distance = 0
        
        return total_distance, avg_speed
    
    async def update_device_status(self, device_id: str, status: str) -> Optional[dict]:
        """Update device status."""
        result = await self.db.devices.find_one_and_update(
            {"device_id": device_id},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}},
            return_document=True
        )
        return result
    
    async def get_online_device_count(self) -> int:
        """Get count of devices that have reported in last 5 minutes."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff_time}}},
            {"$group": {"_id": "$device_id"}},
            {"$count": "count"}
        ]
        
        result = await self.db.gps_locations.aggregate(pipeline).to_list(length=1)
        return result[0]["count"] if result else 0
