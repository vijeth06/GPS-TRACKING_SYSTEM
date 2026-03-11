"""
Ops Service
===========
Operational health snapshot and stream quality metrics.
"""

from datetime import datetime, timedelta
from typing import Dict, Any

from backend.database.connection import get_database


class OpsService:
    def __init__(self):
        self.db = get_database()

    async def snapshot(self) -> Dict[str, Any]:
        now = datetime.utcnow()
        total_devices = await self.db.devices.count_documents({})

        recent_cutoff = now - timedelta(minutes=5)
        delayed_cutoff = now - timedelta(minutes=1)

        online_pipeline = [
            {"$match": {"timestamp": {"$gte": recent_cutoff}}},
            {"$group": {"_id": "$device_id"}},
            {"$count": "count"},
        ]
        delayed_pipeline = [
            {"$match": {"timestamp": {"$lt": delayed_cutoff}}},
            {"$group": {"_id": "$device_id"}},
            {"$count": "count"},
        ]
        packets_last_min = await self.db.raw_packets.count_documents({"created_at": {"$gte": now - timedelta(minutes=1)}})
        failed_last_min = await self.db.raw_packets.count_documents(
            {"created_at": {"$gte": now - timedelta(minutes=1)}, "status": "failed"}
        )

        online = await self.db.gps_locations.aggregate(online_pipeline).to_list(length=1)
        delayed = await self.db.gps_locations.aggregate(delayed_pipeline).to_list(length=1)

        active_alerts = await self.db.alerts.count_documents({"status": {"$in": ["triggered", "acknowledged"]}})
        error_rate = round((failed_last_min / packets_last_min), 3) if packets_last_min else 0.0

        return {
            "total_devices": total_devices,
            "online_devices": online[0]["count"] if online else 0,
            "delayed_devices": delayed[0]["count"] if delayed else 0,
            "active_alerts": active_alerts,
            "packets_last_minute": packets_last_min,
            "packet_error_rate": error_rate,
            "generated_at": now,
        }
