"""Simple in-memory rate limiting service."""

from collections import defaultdict, deque
from threading import Lock
from time import time
from typing import Deque, Dict
import os


class RateLimitService:
    def __init__(self):
        self._buckets: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time()
        lower = now - max(window_seconds, 1)
        with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] < lower:
                bucket.popleft()
            if len(bucket) >= max(limit, 1):
                return False
            bucket.append(now)
            return True


rate_limit_service = RateLimitService()


def _env_int(name: str, default: int, minimum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        val = int(raw)
    except ValueError:
        return default
    return max(val, minimum)


def get_login_rate_limit() -> tuple[int, int]:
    return (
        _env_int("RATE_LIMIT_LOGIN_REQUESTS", 10, 1),
        _env_int("RATE_LIMIT_LOGIN_WINDOW_SECONDS", 60, 1),
    )


def get_ingest_rate_limit() -> tuple[int, int]:
    return (
        _env_int("RATE_LIMIT_INGEST_REQUESTS", 300, 1),
        _env_int("RATE_LIMIT_INGEST_WINDOW_SECONDS", 60, 1),
    )
