"""Pure birthday unlock logic.

Policy:
- Unlock at 00:00 local time on the owner's birthday in their IANA timezone.
- Compare/store moments in UTC.
- February 29 birthdays unlock on February 28 in non-leap years.
"""
import calendar
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def as_utc(dt: datetime) -> datetime:
    """SQLite may return naive datetimes; interpret these as UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def unlock_moment(month: int, day: int, year: int, tz_name: str) -> datetime:
    if month == 2 and day == 29 and not calendar.isleap(year):
        day = 28
    local = datetime(year, month, day, 0, 0, 0, tzinfo=ZoneInfo(tz_name))
    return local.astimezone(timezone.utc)


def is_unlocked(unlock_at: datetime, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    return as_utc(now) >= as_utc(unlock_at)
