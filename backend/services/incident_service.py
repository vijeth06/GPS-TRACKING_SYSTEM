"""
Incident Service
================
Builds an investigation workspace around an alert.
"""

from datetime import timedelta
from typing import Optional, Dict, Any

from bson import ObjectId

from backend.database.connection import get_database
from backend.api.schemas import AlertResponse
from backend.services.alert_service import AlertService
from backend.services.gps_service import GPSService


class IncidentService:
    def __init__(self):
        self.db = get_database()
        self.alert_service = AlertService()
        self.gps_service = GPSService()

    def _to_alert_response(self, alert: Dict[str, Any]) -> AlertResponse:
        return AlertResponse(
            id=str(alert["_id"]),
            device_id=alert["device_id"],
            alert_type=alert["alert_type"],
            severity=alert["severity"],
            message=alert["message"],
            purpose=alert.get("purpose", self.alert_service._infer_purpose(alert.get("alert_type"))),
            latitude=alert.get("latitude"),
            longitude=alert.get("longitude"),
            metadata=alert.get("metadata"),
            is_acknowledged=alert.get("is_acknowledged", False),
            timestamp=alert["timestamp"],
            created_at=alert["created_at"],
            status=alert.get("status", "triggered"),
            acknowledged_at=alert.get("acknowledged_at"),
            resolved_at=alert.get("resolved_at"),
            assigned_to=alert.get("assigned_to"),
            assigned_at=alert.get("assigned_at"),
            assigned_by=alert.get("assigned_by"),
            escalation_level=alert.get("escalation_level", 0),
            escalated_at=alert.get("escalated_at"),
            escalation_due_at=alert.get("escalation_due_at"),
        )

    async def get_open_incidents(self, limit: int = 20):
        cursor = self.db.alerts.find(
            {"status": {"$in": ["triggered", "acknowledged", "assigned", "escalated"]}}
        ).sort("timestamp", -1).limit(limit)
        rows = await cursor.to_list(length=limit)
        return [self._to_alert_response(row) for row in rows]

    async def get_workspace(self, alert_id: str) -> Optional[dict]:
        try:
            alert = await self.db.alerts.find_one({"_id": ObjectId(alert_id)})
        except Exception:
            return None

        if not alert:
            return None

        incident_alert = self._to_alert_response(alert)

        trail_start = alert["timestamp"] - timedelta(minutes=30)
        trail_end = alert["timestamp"] + timedelta(minutes=30)
        trail = await self.gps_service.get_device_trail(alert["device_id"], trail_start, trail_end, limit=1500)

        related_rows = await self.db.alerts.find(
            {
                "device_id": alert["device_id"],
                "timestamp": {"$gte": alert["timestamp"] - timedelta(hours=24), "$lte": alert["timestamp"]},
                "_id": {"$ne": alert["_id"]},
            }
        ).sort("timestamp", -1).limit(25).to_list(length=25)
        related_alerts = [self._to_alert_response(row) for row in related_rows]

        summary = (
            f"Incident for device {alert['device_id']} with {len(related_alerts)} related alerts in prior 24h "
            f"and {len(trail.points) if trail else 0} trail points in +/-30 min window."
        )

        return {
            "alert": incident_alert,
            "related_alerts": related_alerts,
            "recent_trail": trail,
            "investigation_summary": summary,
        }
