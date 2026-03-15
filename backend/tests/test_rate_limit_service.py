from backend.services.rate_limit_service import RateLimitService


def test_rate_limit_allows_until_limit():
    svc = RateLimitService()
    key = "login:127.0.0.1"
    assert svc.check(key, limit=2, window_seconds=60) is True
    assert svc.check(key, limit=2, window_seconds=60) is True
    assert svc.check(key, limit=2, window_seconds=60) is False
