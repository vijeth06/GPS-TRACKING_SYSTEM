from datetime import datetime, timedelta, UTC
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.services.alert_service import AlertService
from backend.services.device_service import DeviceService


def test_alert_severity_escalation_steps():
    svc = AlertService()
    assert svc._escalate_severity("low") == "medium"
    assert svc._escalate_severity("medium") == "high"
    assert svc._escalate_severity("high") == "critical"
    assert svc._escalate_severity("critical") == "critical"


def test_device_connection_status_derivation():
    now = datetime.now(UTC).replace(tzinfo=None)
    assert DeviceService._derive_connection_status(now - timedelta(seconds=20)) == "online"
    assert DeviceService._derive_connection_status(now - timedelta(seconds=180)) == "delayed"
    assert DeviceService._derive_connection_status(now - timedelta(minutes=10)) == "offline"


def test_device_movement_status_derivation():
    assert DeviceService._derive_movement_status(None) == "unknown"
    assert DeviceService._derive_movement_status(1.0) == "stationary"
    assert DeviceService._derive_movement_status(10.0) == "slow"
    assert DeviceService._derive_movement_status(35.0) == "normal"
    assert DeviceService._derive_movement_status(75.0) == "fast"
