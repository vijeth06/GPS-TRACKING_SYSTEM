"""
Alert Service
=============
Business logic for alert management with MongoDB.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

from backend.database.connection import get_database
from backend.models.alert import create_alert_document, alert_to_dict, AlertType, AlertSeverity
from backend.api.schemas import AlertResponse


class AlertService:
    """
    Service class for alert operations.
    
    Handles alert creation, retrieval, and acknowledgement.
    """
    
    def __init__(self):
        self.db = get_database()

    @staticmethod
    def _escalate_severity(current: str) -> str:
        order = [AlertSeverity.LOW, AlertSeverity.MEDIUM, AlertSeverity.HIGH, AlertSeverity.CRITICAL]
        try:
            idx = order.index(current)
        except ValueError:
            return AlertSeverity.MEDIUM
        return order[min(idx + 1, len(order) - 1)]
    
    async def create_alert(
        self,
        device_id: str,
        alert_type: str,
        severity: str,
        message: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> dict:
        """
        Create a new alert.
        
        Args:
            device_id: Device that triggered the alert
            alert_type: Type of alert (stationary, speed, geofence)
            severity: Alert severity level
            message: Human-readable alert message
            latitude: Location where alert was triggered
            longitude: Location where alert was triggered
            metadata: Additional alert-specific data
            
        Returns:
            Created alert as dictionary
        """
        doc = create_alert_document(
            device_id=device_id,
            alert_type=alert_type,
            message=message,
            severity=severity,
            latitude=latitude,
            longitude=longitude,
            metadata=metadata
        )
        
        result = await self.db.alerts.insert_one(doc)
        doc["_id"] = result.inserted_id
        
        return alert_to_dict(doc)
    
    async def get_alerts(
        self,
        device_id: Optional[str] = None,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AlertResponse]:
        """Get alerts with optional filters."""
        query = {}
        
        if device_id:
            query["device_id"] = device_id
        if alert_type:
            query["alert_type"] = alert_type
        if severity:
            query["severity"] = severity
        if start_time or end_time:
            query["timestamp"] = {}
            if start_time:
                query["timestamp"]["$gte"] = start_time
            if end_time:
                query["timestamp"]["$lte"] = end_time
        
        cursor = self.db.alerts.find(query).sort("timestamp", -1).limit(limit)
        alerts = await cursor.to_list(length=limit)
        
        return [
            AlertResponse(
                id=str(alert["_id"]),
                device_id=alert["device_id"],
                alert_type=alert["alert_type"],
                severity=alert["severity"],
                message=alert["message"],
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
            for alert in alerts
        ]
    
    async def get_unacknowledged_alerts(self, limit: int = 50) -> List[AlertResponse]:
        """Get all unacknowledged alerts."""
        cursor = self.db.alerts.find(
            {"is_acknowledged": False}
        ).sort("timestamp", -1).limit(limit)
        
        alerts = await cursor.to_list(length=limit)
        
        return [
            AlertResponse(
                id=str(alert["_id"]),
                device_id=alert["device_id"],
                alert_type=alert["alert_type"],
                severity=alert["severity"],
                message=alert["message"],
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
            for alert in alerts
        ]

    async def assign_alert(
        self,
        alert_id: str,
        assigned_to: str,
        assigned_by: str,
        assignment_note: Optional[str] = None,
    ) -> Optional[AlertResponse]:
        """Assign alert to an operator and track assignment audit."""
        now = datetime.utcnow()
        try:
            alert = await self.db.alerts.find_one_and_update(
                {"_id": ObjectId(alert_id)},
                {
                    "$set": {
                        "assigned_to": assigned_to,
                        "assigned_by": assigned_by,
                        "assigned_at": now,
                        "status": "assigned",
                    }
                },
                return_document=True,
            )
        except:
            return None

        if not alert:
            return None

        await self.db.audit_logs.insert_one(
            {
                "entity_type": "alert",
                "entity_id": str(alert["_id"]),
                "action": "assigned",
                "assigned_to": assigned_to,
                "assigned_by": assigned_by,
                "note": assignment_note,
                "created_at": now,
            }
        )

        return AlertResponse(
            id=str(alert["_id"]),
            device_id=alert["device_id"],
            alert_type=alert["alert_type"],
            severity=alert["severity"],
            message=alert["message"],
            latitude=alert.get("latitude"),
            longitude=alert.get("longitude"),
            metadata=alert.get("metadata"),
            is_acknowledged=alert.get("is_acknowledged", False),
            timestamp=alert["timestamp"],
            created_at=alert["created_at"],
            status=alert.get("status", "assigned"),
            acknowledged_at=alert.get("acknowledged_at"),
            resolved_at=alert.get("resolved_at"),
            assigned_to=alert.get("assigned_to"),
            assigned_at=alert.get("assigned_at"),
            assigned_by=alert.get("assigned_by"),
            escalation_level=alert.get("escalation_level", 0),
            escalated_at=alert.get("escalated_at"),
            escalation_due_at=alert.get("escalation_due_at"),
        )

    async def escalate_alert(
        self,
        alert_id: str,
        escalated_by: str,
        escalation_note: Optional[str] = None,
    ) -> Optional[AlertResponse]:
        """Escalate alert severity and escalation level."""
        try:
            existing = await self.db.alerts.find_one({"_id": ObjectId(alert_id)})
        except:
            return None

        if not existing:
            return None

        now = datetime.utcnow()
        next_level = int(existing.get("escalation_level", 0)) + 1
        next_severity = self._escalate_severity(existing.get("severity", AlertSeverity.MEDIUM))

        try:
            alert = await self.db.alerts.find_one_and_update(
                {"_id": ObjectId(alert_id)},
                {
                    "$set": {
                        "escalation_level": next_level,
                        "escalated_at": now,
                        "severity": next_severity,
                        "status": "escalated",
                    }
                },
                return_document=True,
            )
        except:
            return None

        if not alert:
            return None

        await self.db.audit_logs.insert_one(
            {
                "entity_type": "alert",
                "entity_id": str(alert["_id"]),
                "action": "escalated",
                "escalation_level": next_level,
                "escalated_by": escalated_by,
                "note": escalation_note,
                "created_at": now,
            }
        )

        return AlertResponse(
            id=str(alert["_id"]),
            device_id=alert["device_id"],
            alert_type=alert["alert_type"],
            severity=alert["severity"],
            message=alert["message"],
            latitude=alert.get("latitude"),
            longitude=alert.get("longitude"),
            metadata=alert.get("metadata"),
            is_acknowledged=alert.get("is_acknowledged", False),
            timestamp=alert["timestamp"],
            created_at=alert["created_at"],
            status=alert.get("status", "escalated"),
            acknowledged_at=alert.get("acknowledged_at"),
            resolved_at=alert.get("resolved_at"),
            assigned_to=alert.get("assigned_to"),
            assigned_at=alert.get("assigned_at"),
            assigned_by=alert.get("assigned_by"),
            escalation_level=alert.get("escalation_level", 0),
            escalated_at=alert.get("escalated_at"),
            escalation_due_at=alert.get("escalation_due_at"),
        )
    
    async def acknowledge_alert(self, alert_id: str) -> Optional[AlertResponse]:
        """Acknowledge an alert."""
        try:
            alert = await self.db.alerts.find_one_and_update(
                {"_id": ObjectId(alert_id)},
                {
                    "$set": {
                        "is_acknowledged": True,
                        "status": "acknowledged",
                        "acknowledged_at": datetime.utcnow(),
                    }
                },
                return_document=True
            )
        except:
            return None
        
        if not alert:
            return None
        
        return AlertResponse(
            id=str(alert["_id"]),
            device_id=alert["device_id"],
            alert_type=alert["alert_type"],
            severity=alert["severity"],
            message=alert["message"],
            latitude=alert.get("latitude"),
            longitude=alert.get("longitude"),
            metadata=alert.get("metadata"),
            is_acknowledged=alert.get("is_acknowledged", False),
            timestamp=alert["timestamp"],
            created_at=alert["created_at"],
            status=alert.get("status", "acknowledged"),
            acknowledged_at=alert.get("acknowledged_at"),
            resolved_at=alert.get("resolved_at"),
            assigned_to=alert.get("assigned_to"),
            assigned_at=alert.get("assigned_at"),
            assigned_by=alert.get("assigned_by"),
            escalation_level=alert.get("escalation_level", 0),
            escalated_at=alert.get("escalated_at"),
            escalation_due_at=alert.get("escalation_due_at"),
        )

    async def resolve_alert(self, alert_id: str, resolution_note: Optional[str] = None) -> Optional[AlertResponse]:
        """Resolve an alert and write to audit trail."""
        now = datetime.utcnow()
        try:
            alert = await self.db.alerts.find_one_and_update(
                {"_id": ObjectId(alert_id)},
                {
                    "$set": {
                        "status": "resolved",
                        "resolved_at": now,
                        "is_acknowledged": True,
                        "acknowledged_at": now,
                        "resolution_note": resolution_note,
                    }
                },
                return_document=True,
            )
        except:
            return None

        if not alert:
            return None

        await self.db.audit_logs.insert_one(
            {
                "entity_type": "alert",
                "entity_id": str(alert["_id"]),
                "action": "resolved",
                "note": resolution_note,
                "created_at": datetime.utcnow(),
            }
        )

        return AlertResponse(
            id=str(alert["_id"]),
            device_id=alert["device_id"],
            alert_type=alert["alert_type"],
            severity=alert["severity"],
            message=alert["message"],
            latitude=alert.get("latitude"),
            longitude=alert.get("longitude"),
            metadata=alert.get("metadata"),
            is_acknowledged=alert.get("is_acknowledged", False),
            timestamp=alert["timestamp"],
            created_at=alert["created_at"],
            status=alert.get("status", "resolved"),
            acknowledged_at=alert.get("acknowledged_at"),
            resolved_at=alert.get("resolved_at"),
            assigned_to=alert.get("assigned_to"),
            assigned_at=alert.get("assigned_at"),
            assigned_by=alert.get("assigned_by"),
            escalation_level=alert.get("escalation_level", 0),
            escalated_at=alert.get("escalated_at"),
            escalation_due_at=alert.get("escalation_due_at"),
        )
    
    async def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        # Count by type
        type_pipeline = [
            {"$group": {"_id": "$alert_type", "count": {"$sum": 1}}}
        ]
        type_results = await self.db.alerts.aggregate(type_pipeline).to_list(length=100)
        
        # Count by severity
        severity_pipeline = [
            {"$group": {"_id": "$severity", "count": {"$sum": 1}}}
        ]
        severity_results = await self.db.alerts.aggregate(severity_pipeline).to_list(length=100)
        
        # Total counts
        total = await self.db.alerts.count_documents({})
        unacknowledged = await self.db.alerts.count_documents({"is_acknowledged": False})
        
        return {
            "total": total,
            "unacknowledged": unacknowledged,
            "by_type": {r["_id"]: r["count"] for r in type_results if r["_id"]},
            "by_severity": {r["_id"]: r["count"] for r in severity_results if r["_id"]}
        }
    
    async def get_unacknowledged_count(self) -> int:
        """Get count of unacknowledged alerts."""
        return await self.db.alerts.count_documents({"is_acknowledged": False})
