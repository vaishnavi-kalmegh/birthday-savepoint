from __future__ import annotations

from datetime import date
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.unlock import LEAP_POLICIES
from app.models import Friend
from app.security import generate_one_time_password, hash_password
from app.services import auth
from app.themes import validate_theme


def create_friend(
    db: Session,
    *,
    display_name: str,
    timezone: str,
    birth_month: int,
    birth_day: int,
    theme_key: str,
    theme_config: dict[str, Any] | None = None,
    leap_day_policy: str = "feb28",
    is_admin: bool = False,
) -> tuple[Friend, str]:
    """Create an account and return it with its one-time password (shown once, never stored)."""
    name = display_name.strip()
    if not name or len(name) > 80:
        raise ValueError("display name must be 1 to 80 characters")
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"unknown timezone: {timezone!r}") from exc
    try:
        date(2000, birth_month, birth_day)  # 2000 is a leap year, so Feb 29 is accepted
    except ValueError as exc:
        raise ValueError(f"invalid birthday: {birth_month}-{birth_day}") from exc
    if leap_day_policy not in LEAP_POLICIES:
        raise ValueError(f"unknown leap day policy: {leap_day_policy!r}")
    theme = validate_theme(theme_key, theme_config)

    password = generate_one_time_password()
    friend = Friend(
        display_name=name,
        password_hash=hash_password(password),
        must_change_password=True,
        timezone=timezone,
        birth_month=birth_month,
        birth_day=birth_day,
        leap_day_policy=leap_day_policy,
        theme_key=theme_key,
        theme_config=theme,
        is_admin=is_admin,
    )
    db.add(friend)
    db.commit()
    return friend, password


def reset_password(db: Session, friend: Friend, *, now) -> str:  # type: ignore[no-untyped-def]
    """Issue a new one-time password and revoke every existing session."""
    password = generate_one_time_password()
    auth.set_password(db, friend, password, must_change=True)
    auth.revoke_all_sessions(db, friend.id, now=now)
    return password


def get_by_public_id(db: Session, public_id: str) -> Friend | None:
    return db.execute(select(Friend).where(Friend.public_id == public_id)).scalar_one_or_none()
