"""
Movement Analyzer
=================
Engine for analyzing GPS movement patterns and detecting anomalies.

Key Functions:
- Speed calculation using Haversine formula
- Movement status classification
- Stationary detection
- Speed violation detection
- Total distance calculation

Speed Classifications:
- 0-5 km/h → stationary
- 5-20 km/h → slow
- 20-60 km/h → normal
- >60 km/h → fast
"""

import math
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

from backend.database.connection import get_database


EARTH_RADIUS_KM = 6371.0

SPEED_STATIONARY = 5
SPEED_SLOW = 20
SPEED_NORMAL = 60
SPEED_VIOLATION = 120  # Above this triggers alert

STATIONARY_DISTANCE_THRESHOLD = 0.01  # km (10 meters)
STATIONARY_TIME_THRESHOLD = 300  # seconds (5 minutes)


class MovementAnalyzer:
    """
    Analyzes GPS movement data to extract insights and detect anomalies.
    
    This is the core analytics engine that processes GPS data to:
    1. Calculate speed between consecutive points
    2. Classify movement status
    3. Detect stationary devices
    4. Identify speed violations
    5. Calculate total distance traveled
    """
    
    def __init__(self):
        self.db = get_database()
        self._stationary_cache: Dict[str, Dict[str, Any]] = {}
    
    @staticmethod
    def haversine_distance(
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """
        Calculate the great-circle distance between two points on Earth.
        
        Uses the Haversine formula for accurate distance calculation
        on a sphere (Earth).
        
        Args:
            lat1, lon1: First point coordinates (degrees)
            lat2, lon2: Second point coordinates (degrees)
            
        Returns:
            Distance in kilometers
        """
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return EARTH_RADIUS_KM * c
    
    def calculate_speed(
        self,
        lat1: float, lon1: float, time1: datetime,
        lat2: float, lon2: float, time2: datetime
    ) -> float:
        """
        Calculate speed between two GPS points.
        
        Speed = Distance / Time
        
        Args:
            lat1, lon1, time1: First point
            lat2, lon2, time2: Second point
            
        Returns:
            Speed in km/h
        """
        distance_km = self.haversine_distance(lat1, lon1, lat2, lon2)
        
        time_diff = (time2 - time1).total_seconds() / 3600.0
        
        if time_diff <= 0:
            return 0.0
        
        speed = distance_km / time_diff
        return round(speed, 2)
    
    @staticmethod
    def classify_speed(speed: float) -> str:
        """
        Classify speed into movement categories.
        
        Categories:
        - 0-5 km/h → stationary
        - 5-20 km/h → slow
        - 20-60 km/h → normal
        - >60 km/h → fast
        
        Args:
            speed: Speed in km/h
            
        Returns:
            Status string: 'stationary', 'slow', 'normal', or 'fast'
        """
        if speed < SPEED_STATIONARY:
            return "stationary"
        elif speed < SPEED_SLOW:
            return "slow"
        elif speed < SPEED_NORMAL:
            return "normal"
        else:
            return "fast"
    
    async def check_stationary(
        self,
        device_id: str,
        latitude: float,
        longitude: float,
        timestamp: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Check if device has been stationary too long.
        
        A device is considered stationary if it has moved less than
        10 meters in the last 5 minutes.
        
        Args:
            device_id: Device identifier
            latitude: Current latitude
            longitude: Current longitude
            timestamp: Current timestamp
            
        Returns:
            Alert data if stationary too long, None otherwise
        """
        start_time = timestamp - timedelta(seconds=STATIONARY_TIME_THRESHOLD)
        
        cursor = self.db.gps_locations.find({
            "device_id": device_id,
            "timestamp": {"$gte": start_time, "$lt": timestamp}
        }).sort("timestamp", 1)
        
        recent_locations = await cursor.to_list(length=1000)
        
        if len(recent_locations) < 2:
            return None
        
        first_loc = recent_locations[0]
        all_stationary = True
        max_distance = 0
        
        for loc in recent_locations[1:]:
            distance = self.haversine_distance(
                first_loc["latitude"], first_loc["longitude"],
                loc["latitude"], loc["longitude"]
            )
            max_distance = max(max_distance, distance)
            
            if distance > STATIONARY_DISTANCE_THRESHOLD:
                all_stationary = False
                break
        
        current_distance = self.haversine_distance(
            first_loc["latitude"], first_loc["longitude"],
            latitude, longitude
        )
        max_distance = max(max_distance, current_distance)
        
        if current_distance > STATIONARY_DISTANCE_THRESHOLD:
            all_stationary = False
        
        if all_stationary:
            cache_key = device_id
            cached = self._stationary_cache.get(cache_key)
            
            if cached:
                last_alert_time = cached.get('last_alert')
                if last_alert_time and (timestamp - last_alert_time).total_seconds() < 600:
                    return None
            
            stationary_duration = (timestamp - recent_locations[0]["timestamp"]).total_seconds()
            
            self._stationary_cache[cache_key] = {
                'start_time': recent_locations[0]["timestamp"],
                'last_alert': timestamp
            }
            
            return {
                "type": "stationary_alert",
                "message": f"Device {device_id} has been stationary for {int(stationary_duration // 60)} minutes",
                "duration_seconds": int(stationary_duration),
                "max_movement_km": round(max_distance, 4),
                "latitude": latitude,
                "longitude": longitude
            }
        else:
            if device_id in self._stationary_cache:
                del self._stationary_cache[device_id]
        
        return None
    
    def check_speed_violation(
        self,
        device_id: str,
        speed: float,
        latitude: float,
        longitude: float
    ) -> Optional[Dict[str, Any]]:
        """
        Check if speed exceeds violation threshold.
        
        Args:
            device_id: Device identifier
            speed: Current speed in km/h
            latitude: Current latitude
            longitude: Current longitude
            
        Returns:
            Alert data if speed violation, None otherwise
        """
        if speed > SPEED_VIOLATION:
            severity = "high" if speed > 150 else "medium"
            
            return {
                "type": "speed_alert",
                "severity": severity,
                "message": f"Device {device_id} exceeded speed limit: {round(speed, 1)} km/h",
                "speed": round(speed, 2),
                "threshold": SPEED_VIOLATION,
                "latitude": latitude,
                "longitude": longitude
            }
        
        return None
    
    def calculate_total_distance_from_docs(self, locations: List[dict]) -> float:
        """
        Calculate total distance traveled from a list of location documents.
        
        Sums the distance between consecutive points.
        
        Args:
            locations: List of GPS location documents in chronological order
            
        Returns:
            Total distance in kilometers
        """
        if len(locations) < 2:
            return 0.0
        
        total_distance = 0.0
        
        for i in range(1, len(locations)):
            prev = locations[i - 1]
            curr = locations[i]
            
            distance = self.haversine_distance(
                prev["latitude"], prev["longitude"],
                curr["latitude"], curr["longitude"]
            )
            total_distance += distance
        
        return round(total_distance, 2)
    
    async def get_speed_statistics(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, float]:
        """
        Calculate speed statistics for a device in a time range.
        
        Args:
            device_id: Device identifier
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            Dictionary with avg, max, min speeds
        """
        pipeline = [
            {
                "$match": {
                    "device_id": device_id,
                    "timestamp": {"$gte": start_time, "$lte": end_time},
                    "speed": {"$ne": None}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "avg_speed": {"$avg": "$speed"},
                    "max_speed": {"$max": "$speed"},
                    "min_speed": {"$min": "$speed"}
                }
            }
        ]
        
        result = await self.db.gps_locations.aggregate(pipeline).to_list(length=1)
        
        if not result:
            return {"avg": 0, "max": 0, "min": 0}
        
        return {
            "avg": round(result[0].get("avg_speed", 0) or 0, 2),
            "max": round(result[0].get("max_speed", 0) or 0, 2),
            "min": round(result[0].get("min_speed", 0) or 0, 2)
        }