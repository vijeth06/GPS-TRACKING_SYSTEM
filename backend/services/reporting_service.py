"""Reporting service for operational and business KPIs."""

from datetime import datetime, timedelta
from typing import Dict, Any

from backend.database.connection import get_database


class ReportingService:
    def __init__(self):
        self.db = get_database()

    async def summary(self, hours: int) -> Dict[str, Any]:
        now = datetime.utcnow()
        start = now - timedelta(hours=hours)

        total_packets = await self.db.raw_packets.count_documents({"created_at": {"$gte": start}})
        total_alerts = await self.db.alerts.count_documents({"timestamp": {"$gte": start}})
        resolved_alerts = await self.db.alerts.count_documents(
            {"resolved_at": {"$gte": start}, "status": "resolved"}
        )
        route_deviation_events = await self.db.route_deviation_events.count_documents(
            {"timestamp": {"$gte": start}}
        )

        active_devices = len(
            await self.db.gps_locations.distinct("device_id", {"timestamp": {"$gte": start}})
        )

        speed_pipeline = [
            {"$match": {"timestamp": {"$gte": start}, "speed": {"$ne": None}}},
            {"$group": {"_id": None, "avg_speed": {"$avg": "$speed"}}},
        ]
        speed_result = await self.db.gps_locations.aggregate(speed_pipeline).to_list(length=1)
        avg_speed = round(speed_result[0].get("avg_speed", 0.0), 2) if speed_result else 0.0

        return {
            "hours": hours,
            "total_packets": total_packets,
            "total_alerts": total_alerts,
            "resolved_alerts": resolved_alerts,
            "route_deviation_events": route_deviation_events,
            "active_devices": active_devices,
            "avg_speed": avg_speed,
            "generated_at": now,
        }
