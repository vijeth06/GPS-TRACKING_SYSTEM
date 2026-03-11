"""
Advanced GPS Simulator with Route Following
==========================================
Enhanced simulator that follows predefined routes for more realistic movement.

Features:
- Follows actual road-like paths
- Includes waypoints for turns
- Simulates traffic conditions
- Generates intentional geofence entries for testing
"""

import asyncio
import aiohttp
import random
import math
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import json


# =============================================================================
# CONFIGURATION
# =============================================================================

API_URL = "http://localhost:8000/api/gps"
UPDATE_INTERVAL = 2  # seconds


# =============================================================================
# ROUTE DEFINITIONS
# =============================================================================

# Predefined routes around Coimbatore, India
# Each route is a list of (lat, lng) waypoints

ROUTES = {
    "route_1": [  # Main city route
        (11.0168, 76.9558),  # Start - Coimbatore center
        (11.0200, 76.9600),
        (11.0250, 76.9650),
        (11.0280, 76.9700),  # Turn point
        (11.0300, 76.9750),
        (11.0280, 76.9800),
        (11.0250, 76.9850),
        (11.0200, 76.9900),  # Turn back
        (11.0168, 76.9850),
        (11.0150, 76.9800),
        (11.0130, 76.9750),
        (11.0150, 76.9700),
        (11.0168, 76.9650),
        (11.0168, 76.9558),  # Return to start
    ],
    "route_2": [  # Industrial area route
        (11.0050, 76.9400),
        (11.0080, 76.9450),
        (11.0100, 76.9500),
        (11.0120, 76.9550),
        (11.0100, 76.9600),
        (11.0080, 76.9650),
        (11.0050, 76.9600),
        (11.0030, 76.9550),
        (11.0050, 76.9500),
        (11.0050, 76.9400),
    ],
    "route_3": [  # Highway route (faster speeds)
        (11.0300, 76.9200),
        (11.0350, 76.9300),
        (11.0400, 76.9400),
        (11.0450, 76.9500),
        (11.0500, 76.9600),
        (11.0550, 76.9700),
        (11.0600, 76.9800),
        (11.0550, 76.9750),
        (11.0500, 76.9700),
        (11.0450, 76.9650),
        (11.0400, 76.9600),
        (11.0350, 76.9500),
        (11.0300, 76.9400),
        (11.0300, 76.9200),
    ],
    "geofence_test": [  # Route that passes through geofence areas
        (11.0168, 76.9558),
        (11.2700, 77.6000),  # Approaching geofence
        (11.2750, 77.6050),  # Inside Warehouse Zone A geofence!
        (11.2800, 77.6100),
        (11.2850, 77.6150),
        (11.2900, 77.6200),
        (11.2850, 77.6250),
        (11.2800, 77.6200),
        (11.2750, 77.6150),
        (11.2700, 77.6100),
        (11.0168, 76.9558),
    ],
}


@dataclass
class RouteFollower:
    """Device that follows a predefined route."""
    device_id: str
    device_name: str
    route_name: str
    route_points: List[Tuple[float, float]]
    current_index: int = 0
    progress: float = 0.0  # 0.0 to 1.0 between waypoints
    base_speed: float = 40.0  # km/h
    latitude: float = 0.0
    longitude: float = 0.0
    speed: float = 0.0
    heading: float = 0.0
    is_stopped: bool = False
    stop_timer: int = 0
    
    def __post_init__(self):
        if self.route_points:
            self.latitude = self.route_points[0][0]
            self.longitude = self.route_points[0][1]
    
    def to_payload(self) -> dict:
        return {
            "device_id": self.device_id,
            "latitude": round(self.latitude, 6),
            "longitude": round(self.longitude, 6),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "speed": round(self.speed, 2),
            "heading": round(self.heading, 2)
        }


def calculate_bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate bearing between two points."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lng = math.radians(lng2 - lng1)
    
    x = math.sin(delta_lng) * math.cos(lat2_rad)
    y = (math.cos(lat1_rad) * math.sin(lat2_rad) -
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lng))
    
    bearing = math.atan2(x, y)
    return (math.degrees(bearing) + 360) % 360


def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points in km."""
    R = 6371.0
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def interpolate_position(
    lat1: float, lng1: float,
    lat2: float, lng2: float,
    progress: float
) -> Tuple[float, float]:
    """Interpolate position between two points."""
    lat = lat1 + (lat2 - lat1) * progress
    lng = lng1 + (lng2 - lng1) * progress
    return lat, lng


def update_route_follower(device: RouteFollower, time_seconds: float) -> None:
    """Update device position along route."""
    # Handle stops
    if device.is_stopped:
        device.stop_timer -= 1
        if device.stop_timer <= 0:
            device.is_stopped = False
            device.speed = device.base_speed * 0.5
        else:
            device.speed = 0
            return
    
    # Random stop chance
    if random.random() < 0.03:
        device.is_stopped = True
        device.stop_timer = random.randint(2, 8)
        device.speed = 0
        return
    
    # Get current and next waypoint
    current_point = device.route_points[device.current_index]
    next_index = (device.current_index + 1) % len(device.route_points)
    next_point = device.route_points[next_index]
    
    # Calculate distance to next waypoint
    segment_distance = calculate_distance(
        current_point[0], current_point[1],
        next_point[0], next_point[1]
    )
    
    # Calculate speed with variation
    speed_variation = random.uniform(-10, 10)
    device.speed = max(5, min(100, device.base_speed + speed_variation))
    
    # Calculate movement
    distance_traveled = (device.speed / 3600) * time_seconds  # km
    
    if segment_distance > 0:
        progress_increment = distance_traveled / segment_distance
        device.progress += progress_increment
    
    # Move to next segment if needed
    while device.progress >= 1.0:
        device.progress -= 1.0
        device.current_index = next_index
        next_index = (device.current_index + 1) % len(device.route_points)
        current_point = device.route_points[device.current_index]
        next_point = device.route_points[next_index]
    
    # Interpolate current position
    device.latitude, device.longitude = interpolate_position(
        current_point[0], current_point[1],
        next_point[0], next_point[1],
        device.progress
    )
    
    # Calculate heading
    device.heading = calculate_bearing(
        device.latitude, device.longitude,
        next_point[0], next_point[1]
    )


async def send_gps_data(session: aiohttp.ClientSession, device: RouteFollower) -> bool:
    """Send GPS data to API."""
    payload = device.to_payload()
    
    try:
        async with session.post(API_URL, json=payload) as response:
            if response.status == 200:
                result = await response.json()
                alerts = result.get('alerts', [])
                if alerts:
                    for alert in alerts:
                        print(f"  🚨 ALERT ({device.device_id}): {alert.get('message')}")
                return True
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def create_devices() -> List[RouteFollower]:
    """Create devices following different routes."""
    devices = []
    
    # Create route followers
    route_configs = [
        ("TRK101", "City Delivery 1", "route_1", 45),
        ("TRK102", "City Delivery 2", "route_1", 35),
        ("TRK103", "Industrial Van", "route_2", 30),
        ("TRK104", "Highway Express", "route_3", 70),
        ("TRK105", "Geofence Tester", "geofence_test", 50),
        ("TRK106", "City Patrol 1", "route_1", 40),
        ("TRK107", "Industrial Route 2", "route_2", 35),
    ]
    
    for device_id, name, route_name, speed in route_configs:
        route_points = ROUTES[route_name]
        # Start at random point in route
        start_index = random.randint(0, len(route_points) - 1)
        
        device = RouteFollower(
            device_id=device_id,
            device_name=name,
            route_name=route_name,
            route_points=route_points,
            current_index=start_index,
            base_speed=speed
        )
        devices.append(device)
    
    return devices


async def run_simulation():
    """Main simulation loop."""
    print("=" * 60)
    print("ADVANCED GPS SIMULATOR - ROUTE FOLLOWING MODE")
    print("=" * 60)
    print(f"\n🚀 API Target: {API_URL}")
    print(f"⏱️  Update interval: {UPDATE_INTERVAL}s")
    print("\nPress Ctrl+C to stop\n")
    
    devices = create_devices()
    
    print("📱 Devices:")
    for d in devices:
        print(f"   • {d.device_id}: {d.device_name} ({d.route_name})")
    print()
    
    async with aiohttp.ClientSession() as session:
        update_count = 0
        
        while True:
            update_count += 1
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{ts}] Update #{update_count}")
            
            for device in devices:
                update_route_follower(device, UPDATE_INTERVAL)
                status = "🛑" if device.is_stopped else f"🚗 {device.speed:.0f}km/h"
                print(f"   {device.device_id}: ({device.latitude:.4f}, {device.longitude:.4f}) {status}")
            
            tasks = [send_gps_data(session, d) for d in devices]
            results = await asyncio.gather(*tasks)
            print(f"   ✓ Sent {sum(results)}/{len(devices)}")
            
            await asyncio.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(run_simulation())
    except KeyboardInterrupt:
        print("\n⏹️  Stopped")
