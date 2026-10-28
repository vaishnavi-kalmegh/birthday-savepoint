"""Bounded in-process login throttle; use a shared store before multi-worker deployment."""
import time

MAX_FAILS = 5
WINDOW = 15 * 60
MAX_KEYS = 10_000
_fails: dict[str, list[float]] = {}


def _now(value: float | None = None) -> float:
    return time.monotonic() if value is None else value


def _prune(key: str, now: float | None = None) -> list[float]:
    current = _now(now)
    attempts = [stamp for stamp in _fails.get(key, []) if stamp > current - WINDOW]
    if attempts:
        _fails[key] = attempts
    else:
        _fails.pop(key, None)
    return attempts


def is_blocked(key: str, now: float | None = None) -> bool:
    return len(_prune(key, now)) >= MAX_FAILS


def record_failure(key: str, now: float | None = None) -> None:
    current = _now(now)
    attempts = _prune(key, current)
    if key not in _fails:
        # Prune stale keys before enforcing the hard cap. If an attacker cycles
        # arbitrary identifiers, memory remains bounded even under sustained load.
        if len(_fails) >= MAX_KEYS:
            for existing in list(_fails):
                _prune(existing, current)
        if len(_fails) >= MAX_KEYS:
            # Evict the least-recently-failed key. This is a bounded fallback, not
            # a substitute for a shared, abuse-resistant production rate limiter.
            oldest = min(_fails, key=lambda existing: _fails[existing][-1])
            del _fails[oldest]
        _fails[key] = []
        attempts = _fails[key]
    attempts.append(current)


def reset(key: str) -> None:
    _fails.pop(key, None)


def clear_all() -> None:
    _fails.clear()
