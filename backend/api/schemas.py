"""
Pydantic Schemas
================
Request and response models for API validation.
"""

from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Optional, List
from datetime import datetime


# =============================================================================
# AUTH SCHEMAS
# =============================================================================

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=3, max_length=128)


class UserResponse(BaseModel):
    id: str
    username: str
    full_name: Optional[str] = None
    role: str
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# =============================================================================
# GPS DATA SCHEMAS
# =============================================================================

class GPSDataInput(BaseModel):
    """Schema for incoming GPS data from devices/simulator"""
    device_id: str = Field(..., description="Unique device identifier")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    timestamp: datetime = Field(..., description="GPS reading timestamp")
    altitude: Optional[float] = Field(None, description="Altitude in meters")
    speed: Optional[float] = Field(None, ge=0, description="Speed in km/h")
    heading: Optional[float] = Field(None, ge=0, le=360, description="Heading in degrees")
    accuracy: Optional[float] = Field(None, ge=0, description="Accuracy in meters")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_id": "TRK101",
                "latitude": 11.2754,
                "longitude": 77.6072,
                "timestamp": "2026-03-10T10:01:22",
                "speed": 45.5,
                "heading": 180.0
            }
        }
    )


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
    
    model_config = ConfigDict(from_attributes=True)


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
    
    model_config = ConfigDict(from_attributes=True)


class DeviceWithLocation(DeviceResponse):
    """Device with its latest location"""
    latest_location: Optional[GPSDataResponse] = None
    total_distance: Optional[float] = None
    average_speed: Optional[float] = None
    connection_status: Optional[str] = "offline"  # online, delayed, offline
    movement_status: Optional[str] = "unknown"  # stationary, slow, normal, fast
    last_seen: Optional[datetime] = None


class DeviceOnboardRequest(BaseModel):
    """Schema for onboarding/credential provisioning."""
    device_id: str = Field(..., min_length=1, max_length=64)
    device_name: Optional[str] = Field(None, max_length=100)
    device_type: Optional[str] = Field("vehicle", max_length=50)


class DeviceUpdateRequest(BaseModel):
    """Schema for updating a managed device."""
    device_name: Optional[str] = Field(None, max_length=100)
    device_type: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=32)


class DeviceDeleteResponse(BaseModel):
    """Response after deleting a device and related telemetry."""
    device_id: str
    deleted: bool
    deleted_locations: int = 0
    deleted_alerts: int = 0
    deleted_raw_packets: int = 0
    deleted_route_plans: int = 0
    deleted_route_events: int = 0
    deleted_trips: int = 0
    deleted_anomalies: int = 0


class DeviceCredentialResponse(BaseModel):
    """Schema for one-time credential issuance response."""
    device_id: str
    api_key: str
    credential_active: bool
    rotated_at: datetime
    created: bool


class DeviceCredentialStatusResponse(BaseModel):
    """Credential metadata response (does not expose API key)."""
    device_id: str
    credential_active: bool
    rotated_at: Optional[datetime] = None


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
    
    model_config = ConfigDict(from_attributes=True)


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
    assigned_to: Optional[str] = None
    assigned_at: Optional[datetime] = None
    assigned_by: Optional[str] = None
    escalation_level: Optional[int] = 0
    escalated_at: Optional[datetime] = None
    escalation_due_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class AlertAcknowledge(BaseModel):
    """Schema for acknowledging an alert"""
    alert_id: str


class AlertResolve(BaseModel):
    """Schema for resolving an alert"""
    resolution_note: Optional[str] = None


class AlertAssign(BaseModel):
    """Schema for assigning an alert to an operator."""
    assigned_to: str = Field(..., min_length=2, max_length=64)
    assignment_note: Optional[str] = Field(None, max_length=256)


class AlertEscalate(BaseModel):
    """Schema for escalating an alert."""
    escalation_note: Optional[str] = Field(None, max_length=256)


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


class GeoserverConfigStatus(BaseModel):
    wfs_url: Optional[str] = None
    wms_url: Optional[str] = None
    layer_names: List[str] = []
    has_runtime_override: bool = False
    wfs_reachable: Optional[bool] = None


class GeoserverConfigUpdate(BaseModel):
    layer_names: List[str] = Field(default_factory=list)


class OpsSnapshot(BaseModel):
    total_devices: int
    online_devices: int
    delayed_devices: int
    active_alerts: int
    packets_last_minute: int
    packet_error_rate: float
    generated_at: datetime


class RetentionRunResult(BaseModel):
    archived_gps: int
    archived_alerts: int
    archived_packets: int
    cutoff_days: int
    ran_at: datetime


class RetentionStatus(BaseModel):
    enabled: bool
    interval_minutes: int
    cutoff_days: int
    last_run_at: Optional[datetime] = None
    last_result: Optional[RetentionRunResult] = None


class IncidentWorkspaceResponse(BaseModel):
    alert: AlertResponse
    related_alerts: List[AlertResponse]
    recent_trail: DeviceTrailResponse
    investigation_summary: str


class DemoScenarioResult(BaseModel):
    scenario: str
    success: bool
    details: str


# =============================================================================
# NOTIFICATIONS / RULES / ROUTES / ADMIN / REPORTING / GOVERNANCE / INTELLIGENCE
# =============================================================================

class NotificationChannelConfig(BaseModel):
    channel_type: str = Field(..., min_length=2, max_length=32)
    name: str = Field(..., min_length=2, max_length=64)
    enabled: bool = True
    recipient: Optional[str] = Field(None, max_length=128)
    webhook_url: Optional[str] = Field(None, max_length=512)
    severity_filter: List[str] = Field(default_factory=lambda: ["medium", "high", "critical"])


class NotificationChannelResponse(NotificationChannelConfig):
    id: str
    created_at: datetime
    updated_at: datetime


class NotificationTestRequest(BaseModel):
    message: str = Field(..., min_length=3, max_length=256)
    severity: str = Field("medium", min_length=3, max_length=16)


class NotificationDispatchResult(BaseModel):
    delivered: bool
    provider: str
    details: str
    dispatched_at: datetime


class RuleCondition(BaseModel):
    field: str = Field(..., min_length=2, max_length=64)
    op: str = Field(..., min_length=1, max_length=16)
    value: str = Field(..., min_length=1, max_length=128)


class RuleAction(BaseModel):
    action_type: str = Field(..., min_length=2, max_length=32)
    target: Optional[str] = Field(None, max_length=128)
    payload: Optional[dict] = None


class RuleDefinition(BaseModel):
    name: str = Field(..., min_length=3, max_length=80)
    description: Optional[str] = Field(None, max_length=256)
    event_type: str = Field(..., min_length=3, max_length=64)
    enabled: bool = True
    priority: int = Field(100, ge=1, le=1000)
    conditions: List[RuleCondition] = Field(default_factory=list)
    actions: List[RuleAction] = Field(default_factory=list)


class RuleResponse(RuleDefinition):
    id: str
    created_at: datetime
    updated_at: datetime


class RuleEvaluationResult(BaseModel):
    matched_rule_ids: List[str] = []
    executed_actions: List[str] = []


class RouteWaypoint(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    sequence: int = Field(..., ge=0)


class RoutePlanCreate(BaseModel):
    route_name: str = Field(..., min_length=3, max_length=100)
    device_id: str = Field(..., min_length=1, max_length=64)
    deviation_threshold_m: int = Field(250, ge=50, le=5000)
    active: bool = True
    waypoints: List[RouteWaypoint] = Field(default_factory=list)


class RoutePlanResponse(RoutePlanCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class RouteDeviationEvent(BaseModel):
    route_id: str
    device_id: str
    distance_m: float
    threshold_m: float
    latitude: float
    longitude: float
    timestamp: datetime


class AdminUserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=3, max_length=128)
    full_name: Optional[str] = Field(None, max_length=128)
    role: str = Field("viewer", min_length=3, max_length=32)
    is_active: bool = True


class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=128)
    role: Optional[str] = Field(None, min_length=3, max_length=32)
    is_active: Optional[bool] = None


class TeamCreate(BaseModel):
    team_name: str = Field(..., min_length=2, max_length=100)
    lead_username: Optional[str] = Field(None, max_length=64)
    members: List[str] = Field(default_factory=list)
    on_call: bool = False


class TeamResponse(TeamCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class ReportingWindow(BaseModel):
    hours: int = Field(24, ge=1, le=24 * 90)


class ReportingSummary(BaseModel):
    hours: int
    total_packets: int
    total_alerts: int
    resolved_alerts: int
    route_deviation_events: int
    active_devices: int
    avg_speed: float
    generated_at: datetime


class GovernanceSettings(BaseModel):
    mask_device_identifier: bool = False
    mask_precision_decimals: int = Field(5, ge=2, le=6)
    export_requires_admin: bool = True
    updated_by: Optional[str] = Field(None, max_length=64)


class GovernanceSettingsResponse(GovernanceSettings):
    id: str
    updated_at: datetime


class AnomalyInsight(BaseModel):
    device_id: str
    anomaly_score: float
    reason: str
    measured_at: datetime


class StreamListenerStartRequest(BaseModel):
    protocol: Optional[str] = Field(None, description="udp or tcp")
    host: Optional[str] = Field(None, description="bind host")
    port: Optional[int] = Field(None, ge=1, le=65535)
    dataset_profile: Optional[str] = Field(
        None,
        description="strict | flexible | vendor_x",
    )

    @validator("dataset_profile")
    def validate_dataset_profile(cls, value):
        if value is None:
            return value
        normalized = value.strip().lower()
        allowed = {"strict", "flexible", "vendor_x"}
        if normalized not in allowed:
            raise ValueError("dataset_profile must be one of: strict, flexible, vendor_x")
        return normalized


class StreamListenerStatus(BaseModel):
    running: bool
    protocol: str
    host: str
    port: int
    dataset_profile: str = "flexible"
    received_count: int
    parsed_count: int
    rejected_count: int
    last_packet_at: Optional[datetime] = None
    last_error: Optional[str] = None


class GeoserverEndpointHealth(BaseModel):
    wfs_url: Optional[str] = None
    wms_url: Optional[str] = None
    wfs_ok: Optional[bool] = None
    wms_ok: Optional[bool] = None
    wfs_status_code: Optional[int] = None
    wms_status_code: Optional[int] = None


class GeoserverDiscoveredLayers(BaseModel):
    layer_names: List[str] = []
    source: str = "wfs_get_capabilities"
