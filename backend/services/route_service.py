"""Route planning and deviation detection service."""

from datetime import datetime
from math import radians, sin, cos, sqrt, asin
from typing import Dict, Any, List, Optional

from bson import ObjectId

from backend.database.connection import get_database
from backend.services.alert_rules_service import AlertRulesService
from backend.services.alert_service import AlertService


class RouteService:
    def __init__(self):
        self.db = get_database()
        self.alert_rules = AlertRulesService()
        self.alert_service = AlertService()

    async def list_routes(self, device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = {"active": True}
        if device_id:
            query["device_id"] = device_id
        rows = await self.db.route_plans.find(query).sort("updated_at", -1).to_list(length=300)
        return [self._to_response(row) for row in rows]

    async def create_route(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow()
        doc = {**payload, "created_at": now, "updated_at": now}
        result = await self.db.route_plans.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._to_response(doc)

    async def delete_route(self, route_id: str) -> bool:
        try:
            result = await self.db.route_plans.delete_one({"_id": ObjectId(route_id)})
        except Exception:
            return False
        return result.deleted_count > 0

    async def evaluate_deviation(
        self,
        device_id: str,
        latitude: float,
        longitude: float,
        timestamp: datetime,
    ) -> Optional[Dict[str, Any]]:
        route = await self.db.route_plans.find_one({"device_id": device_id, "active": True})
        if not route or not route.get("waypoints"):
            return None

        min_distance = self._min_distance_to_waypoints(latitude, longitude, route.get("waypoints", []))
        threshold = float(route.get("deviation_threshold_m", 250))

        if min_distance <= threshold:
            return None

        event = {
            "route_id": str(route["_id"]),
            "device_id": device_id,
            "distance_m": round(min_distance, 2),
            "threshold_m": threshold,
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": timestamp,
        }

        await self.db.route_deviation_events.insert_one({**event, "created_at": datetime.utcnow()})

        should_emit = await self.alert_rules.should_emit_alert(device_id, "route_deviation_alert", 180)
        if should_emit:
            await self.alert_service.create_alert(
                device_id=device_id,
                alert_type="route_deviation_alert",
                severity="high",
                message=f"Device deviated from route by {int(min_distance)}m",
                latitude=latitude,
                longitude=longitude,
                metadata=event,
            )
        return event

    @staticmethod
    def _min_distance_to_waypoints(lat: float, lng: float, waypoints: List[Dict[str, Any]]) -> float:
        if not waypoints:
            return 0.0
        distances = [RouteService._haversine_m(lat, lng, p.get("lat"), p.get("lng")) for p in waypoints]
        return min(distances)

    @staticmethod
    def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371000.0
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        return r * c

    @staticmethod
    def _to_response(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(row["_id"]),
            "route_name": row.get("route_name"),
            "device_id": row.get("device_id"),
            "deviation_threshold_m": row.get("deviation_threshold_m", 250),
            "active": row.get("active", True),
            "waypoints": row.get("waypoints", []),
            "created_at": row.get("created_at", datetime.utcnow()),
            "updated_at": row.get("updated_at", datetime.utcnow()),
        }
