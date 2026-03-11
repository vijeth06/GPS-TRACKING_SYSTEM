"""
Analytics Service
=================
Business logic for movement analytics and statistics with MongoDB.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from backend.database.connection import get_database
from backend.api.schemas import (
    DeviceAnalytics, SystemAnalytics, SpeedOverTime, SpeedDataPoint
)
from backend.analytics.movement_analyzer import MovementAnalyzer


class AnalyticsService:
    """
    Service class for analytics operations.
    
    Provides aggregated statistics and insights for devices and system.
    """
    
    def __init__(self):
        self.db = get_database()
        self.movement_analyzer = MovementAnalyzer()
    
    async def get_device_analytics(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[DeviceAnalytics]:
        """
        Get comprehensive analytics for a device.
        
        Args:
            device_id: Device identifier
            start_time: Analysis period start
            end_time: Analysis period end
            
        Returns:
            Device analytics or None if device not found
        """
        # Check device exists
        device = await self.db.devices.find_one({"device_id": device_id})
        
        if not device:
            return None
        
        # Get locations in time range
        cursor = self.db.gps_locations.find({
            "device_id": device_id,
            "timestamp": {"$gte": start_time, "$lte": end_time}
        }).sort("timestamp", 1)
        
        locations = await cursor.to_list(length=10000)
        
        if not locations:
            return DeviceAnalytics(
                device_id=device_id,
                total_distance=0,
                average_speed=0,
                max_speed=0,
                stationary_time=0,
                moving_time=0,
                point_count=0,
                current_status="offline"
            )
        
        # Calculate total distance
        total_distance = self.movement_analyzer.calculate_total_distance_from_docs(locations)
        
        # Calculate speed statistics
        speeds = [loc.get("speed") for loc in locations if loc.get("speed") is not None]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        max_speed = max(speeds) if speeds else 0
        
        # Calculate stationary vs moving time
        stationary_time, moving_time = self._calculate_time_breakdown(locations)
        
        # Get current status from latest location
        latest = locations[-1] if locations else None
        current_status = self.movement_analyzer.classify_speed(
            latest.get("speed", 0) if latest else 0
        )
        
        return DeviceAnalytics(
            device_id=device_id,
            total_distance=round(total_distance, 2),
            average_speed=round(avg_speed, 2),
            max_speed=round(max_speed, 2),
            stationary_time=stationary_time,
            moving_time=moving_time,
            point_count=len(locations),
            current_status=current_status
        )
    
    async def get_system_analytics(self) -> SystemAnalytics:
        """Get system-wide analytics."""
        # Total devices
        total_devices = await self.db.devices.count_documents({})
        
        # Online devices (reported in last 5 minutes)
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        
        online_pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff_time}}},
            {"$group": {"_id": "$device_id"}},
            {"$count": "count"}
        ]
        online_result = await self.db.gps_locations.aggregate(online_pipeline).to_list(length=1)
        devices_online = online_result[0]["count"] if online_result else 0
        
        # Alert counts
        total_alerts = await self.db.alerts.count_documents({})
        unacknowledged_alerts = await self.db.alerts.count_documents({"is_acknowledged": False})
        
        # Aggregate speed (last 24 hours)
        start_time = datetime.utcnow() - timedelta(hours=24)
        
        speed_pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": start_time},
                    "speed": {"$ne": None}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "avg_speed": {"$avg": "$speed"}
                }
            }
        ]
        
        speed_result = await self.db.gps_locations.aggregate(speed_pipeline).to_list(length=1)
        avg_speed = round(speed_result[0]["avg_speed"], 2) if speed_result and speed_result[0].get("avg_speed") else 0
        
        return SystemAnalytics(
            total_devices=total_devices,
            devices_online=devices_online,
            total_alerts=total_alerts,
            unacknowledged_alerts=unacknowledged_alerts,
            total_distance=0,
            average_speed=avg_speed
        )
    
    async def get_speed_over_time(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime,
        interval_minutes: int = 5
    ) -> Optional[SpeedOverTime]:
        """
        Get speed data over time for charting.
        
        Aggregates speed readings by time interval.
        """
        # Check device exists
        device = await self.db.devices.find_one({"device_id": device_id})
        
        if not device:
            return None
        
        # Get speed readings with timestamps
        cursor = self.db.gps_locations.find({
            "device_id": device_id,
            "timestamp": {"$gte": start_time, "$lte": end_time},
            "speed": {"$ne": None}
        }).sort("timestamp", 1)
        
        locations = await cursor.to_list(length=10000)
        
        if not locations:
            return SpeedOverTime(device_id=device_id, data=[])
        
        # Aggregate by interval
        data_points = []
        current_interval_start = locations[0]["timestamp"]
        interval_speeds = []
        
        for loc in locations:
            # Check if still in current interval
            if (loc["timestamp"] - current_interval_start).total_seconds() < interval_minutes * 60:
                interval_speeds.append(loc["speed"])
            else:
                # Save current interval average
                if interval_speeds:
                    avg = sum(interval_speeds) / len(interval_speeds)
                    data_points.append(SpeedDataPoint(
                        timestamp=current_interval_start,
                        speed=round(avg, 2)
                    ))
                
                # Start new interval
                current_interval_start = loc["timestamp"]
                interval_speeds = [loc["speed"]]
        
        # Don't forget last interval
        if interval_speeds:
            avg = sum(interval_speeds) / len(interval_speeds)
            data_points.append(SpeedDataPoint(
                timestamp=current_interval_start,
                speed=round(avg, 2)
            ))
        
        return SpeedOverTime(device_id=device_id, data=data_points)
    
    async def get_heatmap_data(
        self,
        start_time: datetime,
        end_time: datetime,
        resolution: float = 0.001
    ) -> List[Dict[str, Any]]:
        """
        Get location frequency data for heatmap visualization.
        
        Aggregates locations into grid cells and counts occurrences.
        """
        # Use MongoDB aggregation with rounding for grid-based aggregation
        pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": start_time, "$lte": end_time}
                }
            },
            {
                "$project": {
                    "lat": {
                        "$multiply": [
                            {"$round": [{"$divide": ["$latitude", resolution]}, 0]},
                            resolution
                        ]
                    },
                    "lng": {
                        "$multiply": [
                            {"$round": [{"$divide": ["$longitude", resolution]}, 0]},
                            resolution
                        ]
                    }
                }
            },
            {
                "$group": {
                    "_id": {"lat": "$lat", "lng": "$lng"},
                    "count": {"$sum": 1}
                }
            },
            {"$match": {"count": {"$gt": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1000}
        ]
        
        results = await self.db.gps_locations.aggregate(pipeline).to_list(length=1000)
        
        heatmap_data = []
        for row in results:
            heatmap_data.append({
                "lat": row["_id"]["lat"],
                "lng": row["_id"]["lng"],
                "count": row["count"],
                "intensity": min(1.0, row["count"] / 100)
            })
        
        return heatmap_data
    
    def _calculate_time_breakdown(self, locations: List[dict]) -> tuple:
        """Calculate time spent stationary vs moving."""
        if len(locations) < 2:
            return 0, 0
        
        stationary_time = 0
        moving_time = 0
        
        for i in range(1, len(locations)):
            prev = locations[i - 1]
            curr = locations[i]
            
            time_diff = (curr["timestamp"] - prev["timestamp"]).total_seconds()
            speed = curr.get("speed", 0) or 0
            
            if speed < 5:  # stationary threshold
                stationary_time += time_diff
            else:
                moving_time += time_diff
        
        return int(stationary_time), int(moving_time)
        """
        Get speed data over time for charting.
        
        Aggregates speed readings by time interval.
        """
        # Check device exists
        device = self.db.query(Device)\
            .filter(Device.device_id == device_id)\
            .first()
        
        if not device:
            return None
        
        # Get speed readings with timestamps
        locations = self.db.query(GPSLocation.timestamp, GPSLocation.speed)\
            .filter(GPSLocation.device_id == device_id)\
            .filter(GPSLocation.timestamp >= start_time)\
            .filter(GPSLocation.timestamp <= end_time)\
            .filter(GPSLocation.speed.isnot(None))\
            .order_by(GPSLocation.timestamp.asc())\
            .all()
        
        if not locations:
            return SpeedOverTime(device_id=device_id, data=[])
        
        # Aggregate by interval
        data_points = []
        current_interval_start = locations[0].timestamp
        interval_speeds = []
        
        for loc in locations:
            # Check if still in current interval
            if (loc.timestamp - current_interval_start).total_seconds() < interval_minutes * 60:
                interval_speeds.append(loc.speed)
            else:
                # Save current interval average
                if interval_speeds:
                    avg = sum(interval_speeds) / len(interval_speeds)
                    data_points.append(SpeedDataPoint(
                        timestamp=current_interval_start,
                        speed=round(avg, 2)
                    ))
                
                # Start new interval
                current_interval_start = loc.timestamp
                interval_speeds = [loc.speed]
        
        # Don't forget last interval
        if interval_speeds:
            avg = sum(interval_speeds) / len(interval_speeds)
            data_points.append(SpeedDataPoint(
                timestamp=current_interval_start,
                speed=round(avg, 2)
            ))
        
        return SpeedOverTime(device_id=device_id, data=data_points)
    
    async def get_heatmap_data(
        self,
        start_time: datetime,
        end_time: datetime,
        resolution: float = 0.001
    ) -> List[Dict[str, Any]]:
        """
        Get location frequency data for heatmap visualization.
        
        Aggregates locations into grid cells and counts occurrences.
        """
        # MongoDB aggregation to group by rounded coordinates
        pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": start_time, "$lte": end_time}
                }
            },
            {
                "$group": {
                    "_id": {
                        "lat": {
                            "$multiply": [
                                {"$round": [{"$divide": ["$latitude", resolution]}, 0]},
                                resolution
                            ]
                        },
                        "lng": {
                            "$multiply": [
                                {"$round": [{"$divide": ["$longitude", resolution]}, 0]},
                                resolution
                            ]
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {"$match": {"count": {"$gt": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1000}
        ]
        
        cursor = self.db.gps_locations.aggregate(pipeline)
        results = await cursor.to_list(length=1000)
        
        heatmap_data = []
        for row in results:
            heatmap_data.append({
                "lat": float(row["_id"]["lat"]),
                "lng": float(row["_id"]["lng"]),
                "count": row["count"],
                "intensity": min(1.0, row["count"] / 100)  # Normalize intensity
            })
        
        return heatmap_data
    
    def _calculate_time_breakdown(
        self,
        locations: List[dict]
    ) -> tuple:
        """Calculate stationary vs moving time from locations."""
        stationary_time = 0
        moving_time = 0
        
        for i in range(1, len(locations)):
            prev = locations[i - 1]
            curr = locations[i]
            
            time_diff = (curr["timestamp"] - prev["timestamp"]).total_seconds()
            
            # Use speed to determine if stationary or moving
            avg_speed = 0
            prev_speed = prev.get("speed")
            curr_speed = curr.get("speed")
            
            if prev_speed is not None and curr_speed is not None:
                avg_speed = (prev_speed + curr_speed) / 2
            elif curr_speed is not None:
                avg_speed = curr_speed
            
            if avg_speed < 5:  # Less than 5 km/h is stationary
                stationary_time += time_diff
            else:
                moving_time += time_diff
        
        return int(stationary_time), int(moving_time)
