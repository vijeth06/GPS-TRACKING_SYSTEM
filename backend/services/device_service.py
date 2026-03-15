"""
Device Service
==============
Business logic for device management with MongoDB.
"""

import base64
import hashlib
import hmac
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, UTC
from bson import ObjectId

from backend.database.connection import get_database
from backend.config.runtime import get_connectivity_thresholds_seconds
from backend.models.device import DeviceStatus, create_device_document
from backend.api.schemas import DeviceResponse, DeviceWithLocation, GPSDataResponse


class DeviceService:
    """
    Service class for device operations.
    
    Handles device registration, lookup, and status management.
    """
    
    def __init__(self):
        self.db = get_database()

    @staticmethod
    def _generate_device_api_key() -> str:
        """Generate a random API key shown once during provisioning."""
        token = base64.urlsafe_b64encode(os.urandom(24)).decode("utf-8").rstrip("=")
        return f"dvc_{token}"

    @staticmethod
    def _hash_device_api_key(api_key: str, salt: Optional[str] = None) -> Dict[str, str]:
        """Hash device API key with PBKDF2 for at-rest protection."""
        if not salt:
            salt = base64.b64encode(os.urandom(16)).decode("utf-8")
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            api_key.encode("utf-8"),
            salt.encode("utf-8"),
            120000,
        )
        return {
            "credential_salt": salt,
            "credential_hash": base64.b64encode(digest).decode("utf-8"),
        }

    @staticmethod
    def _derive_connection_status(last_timestamp: Optional[datetime]) -> str:
        """Classify connectivity based on recency of the last GPS update."""
        if not last_timestamp:
            return "offline"

        now = datetime.now(UTC).replace(tzinfo=None)
        delta_seconds = (now - last_timestamp).total_seconds()
        online_seconds, delayed_seconds = get_connectivity_thresholds_seconds()

        if delta_seconds <= online_seconds:
            return "online"
        if delta_seconds <= delayed_seconds:
            return "delayed"
        return "offline"

    @staticmethod
    def _derive_movement_status(speed: Optional[float]) -> str:
        """Classify movement status from speed."""
        if speed is None:
            return "unknown"
        if speed < 5:
            return "stationary"
        if speed < 20:
            return "slow"
        if speed < 60:
            return "normal"
        return "fast"
    
    async def get_device(self, device_id: str) -> Optional[dict]:
        """Get a device by its ID."""
        return await self.db.devices.find_one({"device_id": device_id})

    async def onboard_device(self, device_id: str, device_name: Optional[str] = None, device_type: str = "vehicle") -> Dict[str, Any]:
        """Create or update a device and issue a fresh API key."""
        device = await self.get_device(device_id)
        created = False
        if not device:
            device = await self.get_or_create_device(
                device_id=device_id,
                device_name=device_name,
                device_type=device_type,
            )
            created = True

        if device_name:
            await self.db.devices.update_one(
                {"device_id": device_id},
                {"$set": {"device_name": device_name, "updated_at": datetime.utcnow()}},
            )

        api_key = self._generate_device_api_key()
        hashed = self._hash_device_api_key(api_key)
        rotated_at = datetime.utcnow()

        await self.db.devices.update_one(
            {"device_id": device_id},
            {
                "$set": {
                    **hashed,
                    "credential_active": True,
                    "credential_rotated_at": rotated_at,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        return {
            "device_id": device_id,
            "api_key": api_key,
            "credential_active": True,
            "rotated_at": rotated_at,
            "created": created,
        }

    async def rotate_device_api_key(self, device_id: str) -> Dict[str, Any]:
        """Rotate existing device API key and return new one once."""
        device = await self.get_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")

        api_key = self._generate_device_api_key()
        hashed = self._hash_device_api_key(api_key)
        rotated_at = datetime.utcnow()

        await self.db.devices.update_one(
            {"device_id": device_id},
            {
                "$set": {
                    **hashed,
                    "credential_active": True,
                    "credential_rotated_at": rotated_at,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        return {
            "device_id": device_id,
            "api_key": api_key,
            "credential_active": True,
            "rotated_at": rotated_at,
            "created": False,
        }

    async def get_device_credential_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Return non-secret credential metadata for a device."""
        device = await self.get_device(device_id)
        if not device:
            return None

        return {
            "device_id": device_id,
            "credential_active": bool(device.get("credential_active", False)),
            "rotated_at": device.get("credential_rotated_at"),
        }

    async def verify_device_api_key(self, device_id: str, api_key: str) -> bool:
        """Validate provided device API key against hashed credentials."""
        if not api_key:
            return False

        device = await self.get_device(device_id)
        if not device or not device.get("credential_active"):
            return False

        stored_hash = device.get("credential_hash")
        stored_salt = device.get("credential_salt")
        if not stored_hash or not stored_salt:
            return False

        computed = self._hash_device_api_key(api_key, stored_salt)["credential_hash"]
        return hmac.compare_digest(computed, stored_hash)
    
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
        
        latest_location = await self.db.gps_locations.find_one(
            {"device_id": device_id},
            sort=[("timestamp", -1)]
        )
        
        total_distance, avg_speed = await self._calculate_device_stats(device_id)
        
        location_response = None
        last_seen = None
        connection_status = "offline"
        movement_status = "unknown"
        if latest_location:
            last_seen = latest_location.get("timestamp")
            connection_status = self._derive_connection_status(last_seen)
            movement_status = self._derive_movement_status(latest_location.get("speed"))
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
            average_speed=avg_speed,
            connection_status=connection_status,
            movement_status=movement_status,
            last_seen=last_seen,
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

    async def update_device(
        self,
        device_id: str,
        device_name: Optional[str] = None,
        device_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[dict]:
        """Update editable device fields."""
        updates: Dict[str, Any] = {"updated_at": datetime.utcnow()}
        if device_name is not None:
            updates["device_name"] = device_name.strip() or f"Device {device_id}"
        if device_type is not None:
            updates["device_type"] = device_type.strip() or "vehicle"
        if status is not None:
            updates["status"] = status.strip() or DeviceStatus.ACTIVE.value

        result = await self.db.devices.find_one_and_update(
            {"device_id": device_id},
            {"$set": updates},
            return_document=True,
        )
        return result

    async def delete_device(self, device_id: str) -> Dict[str, Any]:
        """Delete a device and its related telemetry/config documents."""
        device = await self.get_device(device_id)
        if not device:
            return {"device_id": device_id, "deleted": False}

        locations = await self.db.gps_locations.delete_many({"device_id": device_id})
        alerts = await self.db.alerts.delete_many({"device_id": device_id})
        raw_packets = await self.db.raw_packets.delete_many({"payload.device_id": device_id})
        route_plans = await self.db.route_plans.delete_many({"device_id": device_id})
        route_events = await self.db.route_deviation_events.delete_many({"device_id": device_id})
        trips = await self.db.trips.delete_many({"device_id": device_id})
        anomalies = await self.db.anomaly_insights.delete_many({"device_id": device_id})
        await self.db.devices.delete_one({"device_id": device_id})

        return {
            "device_id": device_id,
            "deleted": True,
            "deleted_locations": locations.deleted_count,
            "deleted_alerts": alerts.deleted_count,
            "deleted_raw_packets": raw_packets.deleted_count,
            "deleted_route_plans": route_plans.deleted_count,
            "deleted_route_events": route_events.deleted_count,
            "deleted_trips": trips.deleted_count,
            "deleted_anomalies": anomalies.deleted_count,
        }
    
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