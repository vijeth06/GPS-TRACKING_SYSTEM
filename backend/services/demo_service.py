"""
Demo Service
============
Creates deterministic demo scenarios for hackathon presentations.
"""

from datetime import datetime, timedelta

from backend.database.connection import get_database


class DemoService:
    def __init__(self):
        self.db = get_database()

    async def scenario_geofence_violation(self) -> dict:
        await self.db.geofences.update_one(
            {"name": "Demo Restricted Zone"},
            {
                "$set": {
                    "name": "Demo Restricted Zone",
                    "description": "Hackathon demo zone",
                    "fence_type": "restricted",
                    "is_active": True,
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[76.95, 11.01], [76.97, 11.01], [76.97, 11.03], [76.95, 11.03], [76.95, 11.01]]],
                    },
                    "coordinates": [],
                    "updated_at": datetime.utcnow(),
                },
                "$setOnInsert": {"created_at": datetime.utcnow()},
            },
            upsert=True,
        )
        return {"scenario": "geofence_violation", "success": True, "details": "Demo geofence created"}

    async def scenario_stationary_device(self, device_id: str = "TRK101") -> dict:
        now = datetime.utcnow()
        for i in range(4):
            await self.db.gps_locations.insert_one(
                {
                    "device_id": device_id,
                    "latitude": 11.02,
                    "longitude": 76.96,
                    "location": {"type": "Point", "coordinates": [76.96, 11.02]},
                    "speed": 0.5,
                    "timestamp": now - timedelta(minutes=5) + timedelta(seconds=i * 90),
                    "created_at": datetime.utcnow(),
                }
            )
        return {"scenario": "stationary_behavior", "success": True, "details": f"Stationary points seeded for {device_id}"}
