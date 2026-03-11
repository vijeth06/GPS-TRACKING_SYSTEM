# Models module initialization
# MongoDB document schemas for GPS tracking system

from backend.models.device import DeviceStatus, create_device_document, device_to_dict
from backend.models.gps_location import create_gps_location_document, gps_location_to_dict
from backend.models.geofence import create_geofence_document, geofence_to_dict
from backend.models.alert import create_alert_document, alert_to_dict

__all__ = [
    'DeviceStatus', 'create_device_document', 'device_to_dict',
    'create_gps_location_document', 'gps_location_to_dict',
    'create_geofence_document', 'geofence_to_dict',
    'create_alert_document', 'alert_to_dict'
]
