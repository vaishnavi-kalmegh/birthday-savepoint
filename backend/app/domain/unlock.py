"""Birthday unlock policy. Pure functions, no database or clock access.

Policy (see docs/DECISIONS.md):
- A capsule unlocks at 00:00 on the birthday in the friend's IANA timezone.
- February 29 birthdays in non-leap years use the friend's leap_day_policy: "feb28" or "mar1".
- The unlock moment is the earliest instant whose local date is the birthday date. If local
  midnight falls in a daylight-saving gap, that is the first instant of the day; if it occurs
  twice, the earlier occurrence is used.
"""

from __future__ import annotations

import calendar
from datetime import UTC, date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

LeapPolicy = Literal["feb28", "mar1"]
LEAP_POLICIES: tuple[str, ...] = ("feb28", "mar1")


def birthday_in_year(month: int, day: int, year: int, leap_policy: str) -> date:
    if leap_policy not in LEAP_POLICIES:
        raise ValueError(f"unknown leap day policy: {leap_policy!r}")
    if month == 2 and day == 29 and not calendar.isleap(year):
        return date(year, 2, 28) if leap_policy == "feb28" else date(year, 3, 1)
    return date(year, month, day)


def unlock_moment(
    *, month: int, day: int, tz_name: str, year: int, leap_policy: str = "feb28"
) -> datetime:
    """Return the UTC instant at which the capsule for `year` unlocks."""
    tz = ZoneInfo(tz_name)
    birthday = birthday_in_year(month, day, year, leap_policy)
    # fold=0 (the default) picks the earlier occurrence of an ambiguous time and, for a time
    # inside a gap, the offset before the transition: both give the earliest instant of the day.
    local_midnight = datetime(birthday.year, birthday.month, birthday.day, tzinfo=tz)
    return local_midnight.astimezone(UTC)


def next_sealed_edition(
    *, month: int, day: int, tz_name: str, leap_policy: str, now: datetime
) -> tuple[int, datetime]:
    """The first edition whose unlock moment is still in the future."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now_utc = now.astimezone(UTC)
    # Unlock moments increase with the year, and a local year can differ from the UTC year by at
    # most one, so this window always contains the answer.
    for year in range(now_utc.year - 1, now_utc.year + 3):
        moment = unlock_moment(
            month=month, day=day, tz_name=tz_name, year=year, leap_policy=leap_policy
        )
        if moment > now_utc:
            return year, moment
    raise AssertionError("unreachable: an unlock moment always exists within the window")
