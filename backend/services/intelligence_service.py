"""
Intelligence Service
====================
Quality scoring and trip segmentation features.
"""

from datetime import datetime, timedelta
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

    async def compute_speed_anomaly(self, device_id: str, speed: Optional[float], measured_at: datetime) -> Dict[str, Any]:
        """Return simple anomaly score based on recent speed distribution."""
        if speed is None:
            return {"device_id": device_id, "anomaly_score": 0.0, "reason": "no_speed", "measured_at": measured_at}

        start = measured_at - timedelta(hours=6)
        cursor = self.db.gps_locations.find(
            {"device_id": device_id, "timestamp": {"$gte": start}, "speed": {"$ne": None}},
            {"speed": 1},
        ).sort("timestamp", -1).limit(200)
        rows = await cursor.to_list(length=200)
        speeds = [float(r.get("speed", 0.0)) for r in rows if r.get("speed") is not None]

        if len(speeds) < 10:
            return {"device_id": device_id, "anomaly_score": 0.0, "reason": "insufficient_history", "measured_at": measured_at}

        mean = sum(speeds) / len(speeds)
        variance = sum((x - mean) ** 2 for x in speeds) / len(speeds)
        std = variance ** 0.5
        if std <= 0.01:
            score = 1.0 if abs(speed - mean) > 20 else 0.0
        else:
            z = abs((float(speed) - mean) / std)
            score = min(1.0, round(z / 4.0, 3))

        reason = "speed_outlier" if score >= 0.75 else "normal"
        insight = {
            "device_id": device_id,
            "anomaly_score": score,
            "reason": reason,
            "measured_at": measured_at,
        }
        await self.db.anomaly_insights.insert_one({**insight, "created_at": datetime.utcnow()})
        return insight
