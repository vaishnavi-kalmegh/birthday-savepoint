"""Unlock policy: local midnight in the friend's timezone, with explicit leap-day handling."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.domain.unlock import birthday_in_year, next_sealed_edition, unlock_moment


def test_local_midnight_in_kolkata() -> None:
    moment = unlock_moment(month=3, day=14, tz_name="Asia/Kolkata", year=2027)
    assert moment == datetime(2027, 3, 13, 18, 30, tzinfo=UTC)


def test_daylight_saving_offsets_are_applied_per_date() -> None:
    summer = unlock_moment(month=7, day=4, tz_name="America/Los_Angeles", year=2027)
    winter = unlock_moment(month=1, day=15, tz_name="America/Los_Angeles", year=2027)
    assert summer == datetime(2027, 7, 4, 7, 0, tzinfo=UTC)  # PDT, UTC-7
    assert winter == datetime(2027, 1, 15, 8, 0, tzinfo=UTC)  # PST, UTC-8


def test_far_east_timezone_unlocks_on_the_previous_utc_day() -> None:
    moment = unlock_moment(month=1, day=1, tz_name="Pacific/Kiritimati", year=2027)  # UTC+14
    assert moment == datetime(2026, 12, 31, 10, 0, tzinfo=UTC)


def test_leap_day_in_a_leap_year_is_feb_29() -> None:
    for policy in ("feb28", "mar1"):
        assert birthday_in_year(2, 29, 2028, policy) == date(2028, 2, 29)


def test_leap_day_in_non_leap_year_follows_policy() -> None:
    assert birthday_in_year(2, 29, 2027, "feb28") == date(2027, 2, 28)
    assert birthday_in_year(2, 29, 2027, "mar1") == date(2027, 3, 1)
    # Century years that are not leap years behave the same way.
    assert birthday_in_year(2, 29, 2100, "feb28") == date(2100, 2, 28)
    assert birthday_in_year(2, 29, 2000, "feb28") == date(2000, 2, 29)


def test_leap_day_unlock_moments() -> None:
    kwargs = {"month": 2, "day": 29, "tz_name": "UTC"}
    assert unlock_moment(year=2027, leap_policy="feb28", **kwargs) == datetime(
        2027, 2, 28, tzinfo=UTC
    )
    assert unlock_moment(year=2027, leap_policy="mar1", **kwargs) == datetime(
        2027, 3, 1, tzinfo=UTC
    )
    assert unlock_moment(year=2028, leap_policy="feb28", **kwargs) == datetime(
        2028, 2, 29, tzinfo=UTC
    )


def test_unknown_leap_policy_is_rejected_not_defaulted() -> None:
    with pytest.raises(ValueError):
        birthday_in_year(2, 29, 2027, "whenever")


def test_midnight_inside_a_daylight_saving_gap_is_the_first_instant_of_the_day() -> None:
    # Havana skips 00:00-01:00 on 2027-03-14, so local midnight does not exist.
    moment = unlock_moment(month=3, day=14, tz_name="America/Havana", year=2027)
    tz = ZoneInfo("America/Havana")
    assert moment.astimezone(tz).date() == date(2027, 3, 14)
    assert (moment - timedelta(microseconds=1)).astimezone(tz).date() == date(2027, 3, 13)
    assert moment == datetime(2027, 3, 14, 5, 0, tzinfo=UTC)


def test_midnight_that_occurs_twice_uses_the_earlier_occurrence() -> None:
    # Havana repeats 00:00-01:00 on 2027-11-07 when DST ends.
    moment = unlock_moment(month=11, day=7, tz_name="America/Havana", year=2027)
    tz = ZoneInfo("America/Havana")
    assert (moment - timedelta(microseconds=1)).astimezone(tz).date() == date(2027, 11, 6)
    assert moment == datetime(2027, 11, 7, 4, 0, tzinfo=UTC)  # still on daylight time, UTC-4


@pytest.mark.parametrize(
    "tz_name",
    [
        "UTC",
        "Asia/Kolkata",
        "America/Los_Angeles",
        "America/Sao_Paulo",
        "Pacific/Kiritimati",
        "Pacific/Pago_Pago",
        "Europe/London",
        "Australia/Lord_Howe",
        "America/Havana",
        "Asia/Kathmandu",
    ],
)
@pytest.mark.parametrize("month_day", [(1, 1), (2, 28), (3, 14), (6, 30), (11, 7), (12, 31)])
@pytest.mark.parametrize("year", [2026, 2027, 2028, 2030])
def test_unlock_is_the_earliest_instant_of_the_birthday_in_local_time(
    tz_name: str, month_day: tuple[int, int], year: int
) -> None:
    month, day = month_day
    tz = ZoneInfo(tz_name)
    birthday = birthday_in_year(month, day, year, "feb28")
    moment = unlock_moment(month=month, day=day, tz_name=tz_name, year=year)
    assert moment.astimezone(tz).date() == birthday
    assert (moment - timedelta(microseconds=1)).astimezone(tz).date() < birthday


def test_next_sealed_edition_flips_exactly_at_the_unlock_moment() -> None:
    kwargs = {"month": 3, "day": 14, "tz_name": "Asia/Kolkata", "leap_policy": "feb28"}
    unlock = datetime(2027, 3, 13, 18, 30, tzinfo=UTC)

    year, moment = next_sealed_edition(now=unlock - timedelta(seconds=1), **kwargs)
    assert (year, moment) == (2027, unlock)

    year, moment = next_sealed_edition(now=unlock, **kwargs)
    assert year == 2028
    assert moment == datetime(2028, 3, 13, 18, 30, tzinfo=UTC)

    year, _ = next_sealed_edition(now=unlock + timedelta(days=200), **kwargs)
    assert year == 2028


def test_next_sealed_edition_handles_the_new_year_boundary() -> None:
    kwargs = {"month": 1, "day": 1, "tz_name": "Pacific/Kiritimati", "leap_policy": "feb28"}
    # 2026-12-31 10:00 UTC is already Jan 1, 2027 in Kiritimati: the 2027 capsule has unlocked.
    just_before = datetime(2026, 12, 31, 9, 59, 59, tzinfo=UTC)
    assert next_sealed_edition(now=just_before, **kwargs)[0] == 2027
    at_unlock = datetime(2026, 12, 31, 10, 0, 0, tzinfo=UTC)
    assert next_sealed_edition(now=at_unlock, **kwargs)[0] == 2028


def test_next_sealed_edition_for_a_leap_day_birthday() -> None:
    kwargs = {"month": 2, "day": 29, "tz_name": "UTC", "leap_policy": "feb28"}
    now = datetime(2027, 3, 1, tzinfo=UTC)  # after the Feb 28, 2027 unlock
    year, moment = next_sealed_edition(now=now, **kwargs)
    assert (year, moment) == (2028, datetime(2028, 2, 29, tzinfo=UTC))


def test_naive_now_is_rejected() -> None:
    with pytest.raises(ValueError):
        next_sealed_edition(
            month=3, day=14, tz_name="UTC", leap_policy="feb28", now=datetime(2027, 1, 1)
        )
