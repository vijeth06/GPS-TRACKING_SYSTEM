"""
GPS Service
===========
Business logic for GPS data processing with MongoDB.

Responsibilities:
- Store GPS location data
- Trigger movement analysis
- Check geofence violations
- Broadcast real-time updates
"""

from datetime import datetime, timedelta
from typing import Optional, List

from backend.database.connection import get_database
from backend.models.gps_location import create_gps_location_document
from backend.api.schemas import GPSDataInput, DeviceTrailResponse, TrailPoint, GPSDataResponse
from backend.services.device_service import DeviceService
from backend.services.socket_manager import socket_manager
from backend.analytics.movement_analyzer import MovementAnalyzer
from backend.services.geofence_service import GeofenceService
from backend.services.alert_service import AlertService
from backend.services.alert_rules_service import AlertRulesService
from backend.services.intelligence_service import IntelligenceService
from backend.services.rule_engine_service import RuleEngineService
from backend.services.route_service import RouteService


class GPSService:
    """
    Service class for GPS data operations.
    
    Handles the complete flow of receiving GPS data:
    1. Device registration/lookup
    2. Location storage with GeoJSON point
    3. Movement analysis (speed, status)
    4. Geofence violation checking
    5. Real-time WebSocket broadcasting
    """
    
    def __init__(self):
        self.db = get_database()
        self.device_service = DeviceService()
        self.movement_analyzer = MovementAnalyzer()
        self.geofence_service = GeofenceService()
        self.alert_service = AlertService()
        self.alert_rules = AlertRulesService()
        self.intelligence = IntelligenceService()
        self.rule_engine = RuleEngineService()
        self.route_service = RouteService()
    
    async def process_gps_data(self, gps_data: GPSDataInput) -> dict:
        """
        Process incoming GPS data.
        
        This is the main entry point for GPS data. It performs:
        1. Device registration if new
        2. Location storage
        3. Speed calculation
        4. Movement status determination
        5. Geofence checking
        6. Alert generation
        7. Real-time broadcast
        
        Args:
            gps_data: Incoming GPS payload
            
        Returns:
            Processing result with status and any alerts
        """
        alerts_generated = []
        
        device = await self.device_service.get_or_create_device(gps_data.device_id)
        
        previous_location = await self._get_latest_location(gps_data.device_id)
        
        speed = gps_data.speed
        if speed is None and previous_location:
            speed = self.movement_analyzer.calculate_speed(
                previous_location["latitude"], previous_location["longitude"],
                previous_location["timestamp"],
                gps_data.latitude, gps_data.longitude,
                gps_data.timestamp
            )
        
        location_id = await self._store_location(gps_data, speed)
        
        status = self.movement_analyzer.classify_speed(speed or 0)

        quality_score = self.intelligence.compute_quality_score(gps_data.accuracy, speed)
        trip_state = await self.intelligence.update_trip_state(gps_data.device_id, gps_data.timestamp, speed)
        anomaly = await self.intelligence.compute_speed_anomaly(gps_data.device_id, speed, gps_data.timestamp)
        
        stationary_alert = await self.movement_analyzer.check_stationary(
            gps_data.device_id, gps_data.latitude, gps_data.longitude, gps_data.timestamp
        )
        if stationary_alert and await self.alert_rules.should_emit_alert(gps_data.device_id, "stationary_alert", 300):
            alert = await self.alert_service.create_alert(
                device_id=gps_data.device_id,
                alert_type="stationary_alert",
                severity="medium",
                message=stationary_alert["message"],
                latitude=gps_data.latitude,
                longitude=gps_data.longitude,
                metadata={**stationary_alert, "quality_score": quality_score}
            )
            alerts_generated.append(alert)
        
        speed_alert = self.movement_analyzer.check_speed_violation(
            gps_data.device_id, speed or 0, gps_data.latitude, gps_data.longitude
        )
        if speed_alert and await self.alert_rules.should_emit_alert(gps_data.device_id, "speed_alert", 120):
            alert = await self.alert_service.create_alert(
                device_id=gps_data.device_id,
                alert_type="speed_alert",
                severity=speed_alert["severity"],
                message=speed_alert["message"],
                latitude=gps_data.latitude,
                longitude=gps_data.longitude,
                metadata={**speed_alert, "quality_score": quality_score}
            )
            alerts_generated.append(alert)
        
        violations = await self.geofence_service.check_point_in_geofences(
            gps_data.latitude, gps_data.longitude
        )
        for violation in violations:
            if violation["fence_type"] == "restricted" and await self.alert_rules.should_emit_alert(gps_data.device_id, "geofence_alert", 180):
                alert = await self.alert_service.create_alert(
                    device_id=gps_data.device_id,
                    alert_type="geofence_alert",
                    severity="high",
                    message=f"Device entered restricted zone: {violation['name']}",
                    latitude=gps_data.latitude,
                    longitude=gps_data.longitude,
                    metadata={**violation, "quality_score": quality_score}
                )
                alerts_generated.append(alert)

        route_deviation = await self.route_service.evaluate_deviation(
            device_id=gps_data.device_id,
            latitude=gps_data.latitude,
            longitude=gps_data.longitude,
            timestamp=gps_data.timestamp,
        )

        if anomaly.get("anomaly_score", 0) >= 0.8 and await self.alert_rules.should_emit_alert(gps_data.device_id, "anomaly_alert", 180):
            alert = await self.alert_service.create_alert(
                device_id=gps_data.device_id,
                alert_type="anomaly_alert",
                severity="high",
                message="Anomalous movement pattern detected",
                latitude=gps_data.latitude,
                longitude=gps_data.longitude,
                metadata={"quality_score": quality_score, **anomaly},
            )
            alerts_generated.append(alert)

        rule_eval = await self.rule_engine.evaluate_event(
            "gps_point",
            {
                "device_id": gps_data.device_id,
                "speed": speed or 0,
                "status": status,
                "quality_score": quality_score,
                "anomaly_score": anomaly.get("anomaly_score", 0),
                "route_deviation_m": route_deviation.get("distance_m", 0) if route_deviation else 0,
            },
        )
        
        await self._broadcast_location_update(
            gps_data.device_id,
            gps_data.latitude,
            gps_data.longitude,
            speed,
            status,
            gps_data.timestamp
        )
        
        for alert in alerts_generated:
            await socket_manager.broadcast_alert(alert)
        
        return {
            "success": True,
            "device_id": gps_data.device_id,
            "location_id": location_id,
            "speed": speed,
            "status": status,
            "quality_score": quality_score,
            "trip_state": trip_state,
            "anomaly": anomaly,
            "route_deviation": route_deviation,
            "rule_evaluation": rule_eval,
            "alerts": alerts_generated
        }
    
    async def _store_location(self, gps_data: GPSDataInput, speed: Optional[float]) -> str:
        """Store GPS location with GeoJSON point."""
        doc = create_gps_location_document(
            device_id=gps_data.device_id,
            latitude=gps_data.latitude,
            longitude=gps_data.longitude,
            timestamp=gps_data.timestamp,
            altitude=gps_data.altitude,
            speed=speed,
            heading=gps_data.heading,
            accuracy=gps_data.accuracy
        )
        
        result = await self.db.gps_locations.insert_one(doc)
        return str(result.inserted_id)
    
    async def _get_latest_location(self, device_id: str) -> Optional[dict]:
        """Get the most recent location for a device."""
        return await self.db.gps_locations.find_one(
            {"device_id": device_id},
            sort=[("timestamp", -1)]
        )
    
    async def _broadcast_location_update(
        self,
        device_id: str,
        lat: float,
        lng: float,
        speed: Optional[float],
        status: str,
        timestamp: datetime
    ):
        """Broadcast location update via WebSocket."""
        update = {
            "device_id": device_id,
            "lat": lat,
            "lng": lng,
            "speed": speed,
            "status": status,
            "timestamp": timestamp.isoformat()
        }
        await socket_manager.broadcast_location_update(update)
    
    async def get_device_trail(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000
    ) -> Optional[DeviceTrailResponse]:
        """
        Get device movement trail for visualization.
        
        Returns a list of points that can be drawn as a polyline on the map.
        """
        device = await self.device_service.get_device(device_id)
        if not device:
            return None
        
        cursor = self.db.gps_locations.find(
            {
                "device_id": device_id,
                "timestamp": {"$gte": start_time, "$lte": end_time}
            }
        ).sort("timestamp", 1).limit(limit)
        
        locations = await cursor.to_list(length=limit)
        
        if not locations:
            return DeviceTrailResponse(
                device_id=device_id,
                points=[],
                total_distance=0,
                start_time=start_time,
                end_time=end_time
            )
        
        points = [
            TrailPoint(
                lat=loc["latitude"],
                lng=loc["longitude"],
                timestamp=loc["timestamp"],
                speed=loc.get("speed")
            )
            for loc in locations
        ]
        
        total_distance = self.movement_analyzer.calculate_total_distance_from_docs(locations)
        
        return DeviceTrailResponse(
            device_id=device_id,
            points=points,
            total_distance=total_distance,
            start_time=locations[0]["timestamp"],
            end_time=locations[-1]["timestamp"]
        )
    
    async def get_device_locations(
        self,
        device_id: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        limit: int = 100
    ) -> List[GPSDataResponse]:
        """Get raw GPS location records for a device."""
        query = {"device_id": device_id}
        
        if start_time or end_time:
            query["timestamp"] = {}
            if start_time:
                query["timestamp"]["$gte"] = start_time
            if end_time:
                query["timestamp"]["$lte"] = end_time
        
        cursor = self.db.gps_locations.find(query).sort("timestamp", -1).limit(limit)
        locations = await cursor.to_list(length=limit)
        
        return [
            GPSDataResponse(
                id=str(loc["_id"]),
                device_id=loc["device_id"],
                latitude=loc["latitude"],
                longitude=loc["longitude"],
                altitude=loc.get("altitude"),
                speed=loc.get("speed"),
                heading=loc.get("heading"),
                accuracy=loc.get("accuracy"),
                timestamp=loc["timestamp"],
                created_at=loc["created_at"]
            )
            for loc in locations
        ]