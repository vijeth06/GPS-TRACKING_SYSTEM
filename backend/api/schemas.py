"""
Pydantic Schemas
================
Request and response models for API validation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


# =============================================================================
# GPS DATA SCHEMAS
# =============================================================================

class GPSDataInput(BaseModel):
    """Schema for incoming GPS data from devices/simulator"""
    device_id: str = Field(..., description="Unique device identifier", example="TRK101")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    timestamp: datetime = Field(..., description="GPS reading timestamp")
    altitude: Optional[float] = Field(None, description="Altitude in meters")
    speed: Optional[float] = Field(None, ge=0, description="Speed in km/h")
    heading: Optional[float] = Field(None, ge=0, le=360, description="Heading in degrees")
    accuracy: Optional[float] = Field(None, ge=0, description="Accuracy in meters")
    
    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "TRK101",
                "latitude": 11.2754,
                "longitude": 77.6072,
                "timestamp": "2026-03-10T10:01:22",
                "speed": 45.5,
                "heading": 180.0
            }
        }


class GPSDataResponse(BaseModel):
    """Schema for GPS data response"""
    id: str
    device_id: str
    latitude: float
    longitude: float
    altitude: Optional[float]
    speed: Optional[float]
    heading: Optional[float]
    accuracy: Optional[float]
    timestamp: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


# =============================================================================
# DEVICE SCHEMAS
# =============================================================================

class DeviceCreate(BaseModel):
    """Schema for creating a new device"""
    device_id: str = Field(..., min_length=1, max_length=50)
    device_name: Optional[str] = Field(None, max_length=100)
    device_type: Optional[str] = Field("vehicle", max_length=50)


class DeviceResponse(BaseModel):
    """Schema for device response"""
    id: str
    device_id: str
    device_name: Optional[str]
    device_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DeviceWithLocation(DeviceResponse):
    """Device with its latest location"""
    latest_location: Optional[GPSDataResponse] = None
    total_distance: Optional[float] = None
    average_speed: Optional[float] = None


# =============================================================================
# TRAIL SCHEMAS
# =============================================================================

class TrailPoint(BaseModel):
    """Single point in a device trail"""
    lat: float
    lng: float
    timestamp: datetime
    speed: Optional[float] = None


class DeviceTrailResponse(BaseModel):
    """Response for device trail/history"""
    device_id: str
    points: List[TrailPoint]
    total_distance: float  # km
    start_time: Optional[datetime]
    end_time: Optional[datetime]


# =============================================================================
# GEOFENCE SCHEMAS
# =============================================================================

class CoordinatePoint(BaseModel):
    """A single coordinate point"""
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class GeofenceCreate(BaseModel):
    """Schema for creating a geofence"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    coordinates: List[CoordinatePoint] = Field(..., min_length=3, description="Polygon vertices")
    fence_type: Optional[str] = Field("restricted")


class GeofenceResponse(BaseModel):
    """Schema for geofence response"""
    id: str
    name: str
    description: Optional[str]
    fence_type: str
    is_active: bool
    coordinates: List[CoordinatePoint]
    created_at: datetime
    
    class Config:
        from_attributes = True


# =============================================================================
# ALERT SCHEMAS
# =============================================================================

class AlertResponse(BaseModel):
    """Schema for alert response"""
    id: str
    device_id: str
    alert_type: str
    severity: str
    message: str
    latitude: Optional[float]
    longitude: Optional[float]
    metadata: Optional[dict]
    is_acknowledged: bool
    timestamp: datetime
    created_at: datetime
    status: Optional[str] = "triggered"
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AlertAcknowledge(BaseModel):
    """Schema for acknowledging an alert"""
    alert_id: str


class AlertResolve(BaseModel):
    """Schema for resolving an alert"""
    resolution_note: Optional[str] = None


# =============================================================================
# ANALYTICS SCHEMAS
# =============================================================================

class DeviceAnalytics(BaseModel):
    """Analytics for a single device"""
    device_id: str
    total_distance: float  # km
    average_speed: float  # km/h
    max_speed: float  # km/h
    stationary_time: int  # seconds
    moving_time: int  # seconds
    point_count: int
    current_status: str  # stationary, slow, normal, fast


class SystemAnalytics(BaseModel):
    """Overall system analytics"""
    total_devices: int
    devices_online: int
    total_alerts: int
    unacknowledged_alerts: int
    total_distance: float  # km across all devices
    average_speed: float  # km/h across all devices


class SpeedDataPoint(BaseModel):
    """Speed data point for charts"""
    timestamp: datetime
    speed: float


class SpeedOverTime(BaseModel):
    """Speed data over time for a device"""
    device_id: str
    data: List[SpeedDataPoint]


# =============================================================================
# WEBSOCKET SCHEMAS
# =============================================================================

class LocationUpdate(BaseModel):
    """Real-time location update for WebSocket"""
    device_id: str
    lat: float
    lng: float
    speed: Optional[float]
    status: str  # stationary, slow, normal, fast
    timestamp: datetime


class AlertUpdate(BaseModel):
    """Real-time alert update for WebSocket"""
    id: str
    device_id: str
    alert_type: str
    severity: str
    message: str
    timestamp: datetime


# =============================================================================
# INGESTION / OPS / GEOSERVER SCHEMAS
# =============================================================================

class RawGPSPacket(BaseModel):
    """Raw packet for external port/stream ingestion."""
    device_id: str = Field(..., min_length=1, max_length=64)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    timestamp: datetime
    speed: Optional[float] = Field(None, ge=0)
    heading: Optional[float] = Field(None, ge=0, le=360)
    accuracy: Optional[float] = Field(None, ge=0)
    source: Optional[str] = Field("stream", max_length=64)


class IngestionResult(BaseModel):
    accepted: bool
    deduplicated: bool = False
    reason: Optional[str] = None
    packet_hash: Optional[str] = None


class IngestionStatus(BaseModel):
    queue_size: int
    processed_count: int
    rejected_count: int
    dedup_count: int
    worker_running: bool


class GeoserverLayerInfo(BaseModel):
    layer_name: str
    wfs_enabled: bool = True
    wms_enabled: bool = True
    last_synced_at: Optional[datetime] = None
    feature_count: int = 0


class GeoserverSyncResult(BaseModel):
    layers: List[GeoserverLayerInfo]
    total_features_imported: int
    imported_geofences: int


class OpsSnapshot(BaseModel):
    total_devices: int
    online_devices: int
    delayed_devices: int
    active_alerts: int
    packets_last_minute: int
    packet_error_rate: float
    generated_at: datetime


class DemoScenarioResult(BaseModel):
    scenario: str
    success: bool
    details: str
