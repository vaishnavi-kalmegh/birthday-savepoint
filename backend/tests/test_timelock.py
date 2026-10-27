from datetime import datetime, timedelta, timezone

from app.timelock import is_unlocked, unlock_moment


def test_unlocks_at_local_midnight_in_utc():
    moment = unlock_moment(3, 10, 2027, "Asia/Kolkata")
    assert moment == datetime(2027, 3, 9, 18, 30, tzinfo=timezone.utc)


def test_boundary_one_second_before_and_at_unlock():
    moment = unlock_moment(7, 4, 2027, "UTC")
    assert not is_unlocked(moment, moment - timedelta(seconds=1))
    assert is_unlocked(moment, moment)


def test_leap_day_birthday_policy():
    assert unlock_moment(2, 29, 2028, "UTC").day == 29
    assert unlock_moment(2, 29, 2027, "UTC").day == 28


def test_timezone_matters_around_dst():
    assert unlock_moment(3, 14, 2027, "America/New_York") == datetime(
        2027, 3, 14, 5, 0, tzinfo=timezone.utc
    )
    assert unlock_moment(3, 15, 2027, "America/New_York") == datetime(
        2027, 3, 15, 4, 0, tzinfo=timezone.utc
    )
