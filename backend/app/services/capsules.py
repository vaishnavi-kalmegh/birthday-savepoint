"""Capsule access. Every read goes through the owner + published + unlocked filter in SQL, so a
capsule that is not visible to the caller is never loaded, let alone serialized."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.unlock import next_sealed_edition, unlock_moment
from app.gifts import render_gift, validate_gift
from app.models import Capsule, CapsuleContent, Friend


def _visible(friend: Friend, now: datetime):  # type: ignore[no-untyped-def]
    return (
        Capsule.friend_id == friend.id,
        Capsule.state == "published",
        Capsule.unlock_at <= now,
    )


def list_visible(db: Session, friend: Friend, *, now: datetime) -> list[Capsule]:
    stmt = select(Capsule).where(*_visible(friend, now)).order_by(Capsule.edition_year.desc())
    return list(db.execute(stmt).scalars())


def get_visible(db: Session, friend: Friend, public_id: str, *, now: datetime) -> Capsule | None:
    stmt = select(Capsule).where(Capsule.public_id == public_id, *_visible(friend, now))
    return db.execute(stmt).scalar_one_or_none()


def load_gift(db: Session, capsule: Capsule) -> dict[str, Any]:
    """Load the gift for a capsule the caller has already been authorized to see."""
    row = db.execute(
        select(CapsuleContent).where(CapsuleContent.capsule_id == capsule.id)
    ).scalar_one_or_none()
    if row is None:
        raise LookupError("published capsule has no content")
    return {"type": capsule.content_type, "data": render_gift(capsule.content_type, row.payload)}


def mark_opened(db: Session, capsule: Capsule, *, now: datetime) -> None:
    if capsule.opened_at is None:
        capsule.opened_at = now
        db.commit()


def next_sealed(friend: Friend, *, now: datetime) -> tuple[int, datetime]:
    return next_sealed_edition(
        month=friend.birth_month,
        day=friend.birth_day,
        tz_name=friend.timezone,
        leap_policy=friend.leap_day_policy,
        now=now,
    )


def create_capsule(
    db: Session,
    friend: Friend,
    *,
    edition_year: int,
    content_type: str,
    payload: dict[str, Any],
    publish: bool = False,
    now: datetime,
) -> Capsule:
    """Create a capsule. The unlock moment is derived from the friend's birthday policy only."""
    data = validate_gift(content_type, payload)
    capsule = Capsule(
        friend_id=friend.id,
        edition_year=edition_year,
        unlock_at=unlock_moment(
            month=friend.birth_month,
            day=friend.birth_day,
            tz_name=friend.timezone,
            year=edition_year,
            leap_policy=friend.leap_day_policy,
        ),
        content_type=content_type,
        state="published" if publish else "draft",
        created_at=now,
    )
    db.add(capsule)
    db.flush()
    db.add(CapsuleContent(capsule_id=capsule.id, payload=data))
    db.commit()
    return capsule
