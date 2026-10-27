"""In-process login throttle; not suitable for multi-worker production deployment."""
import time
from collections import defaultdict

MAX_FAILS = 5
WINDOW = 15 * 60
_fails: dict[str, list[float]] = defaultdict(list)


def _prune(key: str) -> list[float]:
    cutoff = time.time() - WINDOW
    _fails[key] = [t for t in _fails[key] if t > cutoff]
    return _fails[key]


def is_blocked(key: str) -> bool:
    return len(_prune(key)) >= MAX_FAILS


def record_failure(key: str) -> None:
    _prune(key).append(time.time())


def reset(key: str) -> None:
    _fails.pop(key, None)


def clear_all() -> None:
    _fails.clear()
