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
                created_at=alert["created_at"]
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
                created_at=alert["created_at"]
            )
            for alert in alerts
        ]
    
    async def acknowledge_alert(self, alert_id: str) -> Optional[AlertResponse]:
        """Acknowledge an alert."""
        try:
            alert = await self.db.alerts.find_one_and_update(
                {"_id": ObjectId(alert_id)},
                {"$set": {"is_acknowledged": True, "acknowledged_at": datetime.utcnow()}},
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
            created_at=alert["created_at"]
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
