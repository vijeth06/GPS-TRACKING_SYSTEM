"""
Intelligence Service
====================
Quality scoring and trip segmentation features.
"""

from datetime import datetime
from typing import Optional, Dict, Any

from backend.database.connection import get_database


class IntelligenceService:
    def __init__(self):
        self.db = get_database()

    def compute_quality_score(self, accuracy: Optional[float], speed: Optional[float]) -> float:
        """Compute a lightweight 0-1 confidence score for a GPS point."""
        score = 1.0
        if accuracy is not None:
            if accuracy > 50:
                score -= 0.4
            elif accuracy > 20:
                score -= 0.2
        if speed is not None and speed > 180:
            score -= 0.3
        return max(0.0, round(score, 2))

    async def update_trip_state(self, device_id: str, timestamp: datetime, speed: Optional[float]) -> Dict[str, Any]:
        """Maintain simple trip start/stop state."""
        moving = (speed or 0) > 5
        active_trip = await self.db.trips.find_one({"device_id": device_id, "status": "active"})

        if moving and not active_trip:
            doc = {
                "device_id": device_id,
                "start_time": timestamp,
                "end_time": None,
                "status": "active",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            result = await self.db.trips.insert_one(doc)
            return {"trip_event": "started", "trip_id": str(result.inserted_id)}

        if not moving and active_trip:
            await self.db.trips.update_one(
                {"_id": active_trip["_id"]},
                {"$set": {"status": "completed", "end_time": timestamp, "updated_at": datetime.utcnow()}},
            )
            return {"trip_event": "ended", "trip_id": str(active_trip["_id"])}

        return {"trip_event": "none", "trip_id": str(active_trip["_id"]) if active_trip else None}
