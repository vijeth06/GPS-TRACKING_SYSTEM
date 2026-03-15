"""Runtime configuration helpers for operational thresholds."""

import os
from typing import Tuple


def _env_int(name: str, default: int, minimum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(value, minimum)


def get_connectivity_thresholds_seconds() -> Tuple[int, int]:
    """Return online and delayed thresholds in seconds."""
    online_seconds = _env_int("DEVICE_ONLINE_SECONDS", 60, 5)
    delayed_seconds = _env_int("DEVICE_DELAYED_SECONDS", 300, online_seconds + 60)
    if delayed_seconds <= online_seconds:
        delayed_seconds = online_seconds + 60
    return online_seconds, delayed_seconds


def get_ingestion_queue_maxsize() -> int:
    """Return max queue size for ingestion worker backpressure."""
    return _env_int("INGEST_QUEUE_MAXSIZE", 10000, 100)
