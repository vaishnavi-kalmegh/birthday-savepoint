from app import ratelimit


def test_rate_limiter_prunes_expired_attempts():
    ratelimit.clear_all()
    for stamp in range(5):
        ratelimit.record_failure("alice", now=float(stamp))
    assert ratelimit.is_blocked("alice", now=5.0)
    assert not ratelimit.is_blocked("alice", now=ratelimit.WINDOW + 4.0)


def test_rate_limiter_caps_arbitrary_keys(monkeypatch):
    ratelimit.clear_all()
    monkeypatch.setattr(ratelimit, "MAX_KEYS", 3)
    for index in range(1000):
        ratelimit.record_failure(f"unknown-{index}", now=float(index))
    assert len(ratelimit._fails) <= 3
    ratelimit.clear_all()
