"""
GPS Simulator
=============
Simulates multiple GPS devices sending real-time location data.

This script creates realistic vehicle movement patterns including:
- Driving along roads
- Stopping at intersections
- Varying speeds
- Random turns

Usage:
    python gps_simulator.py

The simulator will send GPS data to the backend API every 2 seconds
for each simulated device.
"""

import asyncio
import aiohttp
import random
import math
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import List, Tuple
import json



API_URL = "http://localhost:8000/api/gps"

NUM_DEVICES = 7
UPDATE_INTERVAL = 2  # seconds
CENTER_LAT = 11.0168  # Coimbatore, India
CENTER_LNG = 76.9558

MIN_SPEED = 0  # km/h
MAX_SPEED = 80  # km/h
TURN_PROBABILITY = 0.15
STOP_PROBABILITY = 0.05
RESUME_PROBABILITY = 0.3



@dataclass
class SimulatedDevice:
    """Represents a simulated GPS device/vehicle."""
    device_id: str
    device_name: str
    latitude: float
    longitude: float
    speed: float  # km/h
    heading: float  # degrees from north (0-360)
    is_stopped: bool = False
    stop_duration: int = 0
    
    def to_payload(self) -> dict:
        """Convert to API payload format."""
        return {
            "device_id": self.device_id,
            "latitude": round(self.latitude, 6),
            "longitude": round(self.longitude, 6),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "speed": round(self.speed, 2),
            "heading": round(self.heading, 2)
        }



def calculate_new_position(
    lat: float, lng: float,
    speed_kmh: float, heading: float,
    time_seconds: float
) -> Tuple[float, float]:
    """
    Calculate new position based on speed and heading.
    
    Uses simple trigonometry to move along a bearing.
    
    Args:
        lat, lng: Current position
        speed_kmh: Speed in km/h
        heading: Direction in degrees (0 = north, 90 = east)
        time_seconds: Time elapsed
        
    Returns:
        New (latitude, longitude) tuple
    """
    distance_km = (speed_kmh / 3600) * time_seconds
    
    R = 6371.0
    
    lat_rad = math.radians(lat)
    lng_rad = math.radians(lng)
    heading_rad = math.radians(heading)
    
    angular_dist = distance_km / R
    
    new_lat_rad = math.asin(
        math.sin(lat_rad) * math.cos(angular_dist) +
        math.cos(lat_rad) * math.sin(angular_dist) * math.cos(heading_rad)
    )
    
    new_lng_rad = lng_rad + math.atan2(
        math.sin(heading_rad) * math.sin(angular_dist) * math.cos(lat_rad),
        math.cos(angular_dist) - math.sin(lat_rad) * math.sin(new_lat_rad)
    )
    
    return math.degrees(new_lat_rad), math.degrees(new_lng_rad)


def update_device_state(device: SimulatedDevice) -> None:
    """
    Update device position and movement state.
    
    Simulates realistic vehicle behavior:
    - Random stops (like traffic lights)
    - Speed variations
    - Direction changes (turns)
    """
    if device.is_stopped:
        device.stop_duration -= 1
        if device.stop_duration <= 0 or random.random() < RESUME_PROBABILITY:
            device.is_stopped = False
            device.speed = random.uniform(10, 30)  # Resume slowly
        else:
            device.speed = 0
            return
    elif random.random() < STOP_PROBABILITY:
        device.is_stopped = True
        device.stop_duration = random.randint(3, 15)  # Stop for 3-15 updates
        device.speed = 0
        return
    
    speed_change = random.uniform(-5, 5)
    device.speed = max(MIN_SPEED, min(MAX_SPEED, device.speed + speed_change))
    
    if random.random() < TURN_PROBABILITY:
        turn_angle = random.uniform(-45, 45)
        device.heading = (device.heading + turn_angle) % 360
    else:
        device.heading = (device.heading + random.uniform(-5, 5)) % 360
    
    new_lat, new_lng = calculate_new_position(
        device.latitude, device.longitude,
        device.speed, device.heading,
        UPDATE_INTERVAL
    )
    
    device.latitude = new_lat
    device.longitude = new_lng


def create_devices() -> List[SimulatedDevice]:
    """Create initial simulated devices with random starting positions."""
    device_names = [
        "Delivery Truck 1",
        "Delivery Truck 2", 
        "Service Van 1",
        "Service Van 2",
        "Executive Car",
        "Courier Bike 1",
        "Field Agent 1"
    ]
    
    devices = []
    for i in range(NUM_DEVICES):
        lat_offset = random.uniform(-0.05, 0.05)
        lng_offset = random.uniform(-0.05, 0.05)
        
        device = SimulatedDevice(
            device_id=f"TRK{101 + i}",
            device_name=device_names[i] if i < len(device_names) else f"Vehicle {i + 1}",
            latitude=CENTER_LAT + lat_offset,
            longitude=CENTER_LNG + lng_offset,
            speed=random.uniform(20, 50),
            heading=random.uniform(0, 360)
        )
        devices.append(device)
    
    return devices



async def send_gps_data(session: aiohttp.ClientSession, device: SimulatedDevice) -> bool:
    """
    Send GPS data to the backend API.
    
    Args:
        session: aiohttp client session
        device: Device to send data for
        
    Returns:
        True if successful, False otherwise
    """
    payload = device.to_payload()
    
    try:
        async with session.post(API_URL, json=payload) as response:
            if response.status == 200:
                result = await response.json()
                alerts = result.get('alerts', [])
                if alerts:
                    for alert in alerts:
                        print(f"  🚨 ALERT: {alert.get('message', 'Unknown alert')}")
                return True
            else:
                print(f"  ❌ Error sending data for {device.device_id}: {response.status}")
                return False
    except aiohttp.ClientError as e:
        print(f"  ❌ Connection error for {device.device_id}: {e}")
        return False


async def run_simulation():
    """
    Main simulation loop.
    
    Creates devices and continuously sends GPS updates to the backend.
    """
    print("=" * 60)
    print("GPS TRACKING SYSTEM - DEVICE SIMULATOR")
    print("=" * 60)
    print(f"\n🚀 Starting simulation with {NUM_DEVICES} devices")
    print(f"📍 Center location: {CENTER_LAT}, {CENTER_LNG}")
    print(f"⏱️  Update interval: {UPDATE_INTERVAL} seconds")
    print(f"🎯 Target API: {API_URL}")
    print("\nPress Ctrl+C to stop\n")
    print("-" * 60)
    
    devices = create_devices()
    
    print("\n📱 Simulated Devices:")
    for device in devices:
        print(f"   • {device.device_id}: {device.device_name}")
    print()
    
    async with aiohttp.ClientSession() as session:
        update_count = 0
        
        while True:
            update_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{timestamp}] Update #{update_count}")
            
            tasks = []
            for device in devices:
                update_device_state(device)
                
                status = "🛑 STOPPED" if device.is_stopped else f"🚗 {device.speed:.1f} km/h"
                print(f"   {device.device_id}: ({device.latitude:.4f}, {device.longitude:.4f}) {status}")
                
                tasks.append(send_gps_data(session, device))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)
            print(f"   ✓ Sent {success_count}/{len(devices)} updates")
            
            await asyncio.sleep(UPDATE_INTERVAL)



def main():
    """Entry point for the GPS simulator."""
    try:
        asyncio.run(run_simulation())
    except KeyboardInterrupt:
        print("\n\n⏹️  Simulation stopped by user")
    except Exception as e:
        print(f"\n❌ Simulation error: {e}")
        raise


if __name__ == "__main__":
    main()