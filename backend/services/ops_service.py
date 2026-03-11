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

        latest_per_device_pipeline = [
            {"$sort": {"device_id": 1, "timestamp": -1}},
            {
                "$group": {
                    "_id": "$device_id",
                    "last_timestamp": {"$first": "$timestamp"},
                }
            },
        ]

        latest_per_device = await self.db.gps_locations.aggregate(latest_per_device_pipeline).to_list(length=10000)
        online_count = sum(1 for row in latest_per_device if row.get("last_timestamp") and row["last_timestamp"] >= recent_cutoff)
        delayed_count = sum(1 for row in latest_per_device if row.get("last_timestamp") and row["last_timestamp"] < delayed_cutoff)

        packets_last_min = await self.db.raw_packets.count_documents({"created_at": {"$gte": now - timedelta(minutes=1)}})
        failed_last_min = await self.db.raw_packets.count_documents(
            {"created_at": {"$gte": now - timedelta(minutes=1)}, "status": "failed"}
        )

        active_alerts = await self.db.alerts.count_documents({"status": {"$in": ["triggered", "acknowledged"]}})
        error_rate = round((failed_last_min / packets_last_min), 3) if packets_last_min else 0.0

        return {
            "total_devices": total_devices,
            "online_devices": online_count,
            "delayed_devices": delayed_count,
            "active_alerts": active_alerts,
            "packets_last_minute": packets_last_min,
            "packet_error_rate": error_rate,
            "generated_at": now,
        }
