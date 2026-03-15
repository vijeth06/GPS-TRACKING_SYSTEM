from backend.models.alert import AlertType
from backend.services.alert_service import AlertService


def test_infer_purpose_core_alert_types():
    assert AlertService._infer_purpose(AlertType.STATIONARY) == "idle_monitoring"
    assert AlertService._infer_purpose(AlertType.SPEED) == "speed_compliance"
    assert AlertService._infer_purpose(AlertType.GEOFENCE) == "zone_compliance"


def test_infer_purpose_extended_alert_types():
    assert AlertService._infer_purpose("route_deviation_alert") == "route_adherence"
    assert AlertService._infer_purpose("anomaly_alert") == "anomaly_detection"


def test_infer_purpose_fallback():
    assert AlertService._infer_purpose("unknown_type") == "general_monitoring"
