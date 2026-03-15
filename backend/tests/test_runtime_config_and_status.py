from datetime import datetime, timedelta, UTC

from backend.config.runtime import get_connectivity_thresholds_seconds
from backend.services.device_service import DeviceService


def test_connectivity_thresholds_default_order(monkeypatch):
    monkeypatch.delenv("DEVICE_ONLINE_SECONDS", raising=False)
    monkeypatch.delenv("DEVICE_DELAYED_SECONDS", raising=False)
    online, delayed = get_connectivity_thresholds_seconds()
    assert online == 60
    assert delayed == 300
    assert delayed > online


def test_connectivity_thresholds_self_heal_invalid(monkeypatch):
    monkeypatch.setenv("DEVICE_ONLINE_SECONDS", "120")
    monkeypatch.setenv("DEVICE_DELAYED_SECONDS", "90")
    online, delayed = get_connectivity_thresholds_seconds()
    assert online == 120
    assert delayed == 180


def test_device_status_thresholds(monkeypatch):
    monkeypatch.setenv("DEVICE_ONLINE_SECONDS", "60")
    monkeypatch.setenv("DEVICE_DELAYED_SECONDS", "300")

    now = datetime.now(UTC).replace(tzinfo=None)

    assert DeviceService._derive_connection_status(now - timedelta(seconds=30)) == "online"
    assert DeviceService._derive_connection_status(now - timedelta(seconds=180)) == "delayed"
    assert DeviceService._derive_connection_status(now - timedelta(seconds=600)) == "offline"
