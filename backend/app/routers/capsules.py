from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import csrf_protect, current_user
from ..models import Capsule, User
from ..timelock import as_utc, is_unlocked, unlock_moment

router = APIRouter(prefix="/api/capsules", tags=["capsules"])


def _readable(capsule: Capsule) -> bool:
    return capsule.published and is_unlocked(capsule.unlock_at)


def _next_birthday(user: User, today: date) -> tuple[int, datetime]:
    """Return the next birthday year and its unlock instant, without consulting capsules."""
    zone = ZoneInfo(user.timezone)
    this_year_unlock = unlock_moment(
        user.birth_month, user.birth_day, today.year, user.timezone
    )
    this_year_birthday = this_year_unlock.astimezone(zone).date()
    year = today.year if today < this_year_birthday else today.year + 1
    return year, unlock_moment(user.birth_month, user.birth_day, year, user.timezone)


@router.get("")
def list_capsules(user: User = Depends(current_user), db: Session = Depends(get_db)):
    # Select metadata only, and only for published capsules. Never serialize draft or
    # future capsule IDs: their existence is private, even to the capsule's owner.
    rows = db.execute(
        select(
            Capsule.public_id,
            Capsule.year,
            Capsule.unlock_at,
            Capsule.opened_at,
            Capsule.content_type,
        )
        .where(Capsule.owner_id == user.id, Capsule.published.is_(True))
        .order_by(Capsule.year)
    ).all()

    result = []
    for public_id, year, unlock_at, opened_at, content_type in rows:
        if not is_unlocked(unlock_at):
            continue
        result.append({
            "id": public_id,
            "year": year,
            "state": "opened" if opened_at else "available",
            "unlock_at": as_utc(unlock_at).isoformat(),
            "content_type": content_type,
        })

    local_today = datetime.now(ZoneInfo(user.timezone)).date()
    next_year, next_unlock = _next_birthday(user, local_today)
    result.append({
        "year": next_year,
        "state": "sealed",
        "unlock_at": as_utc(next_unlock).isoformat(),
    })
    return sorted(result, key=lambda item: item["year"])


def _owned_readable(public_id: str, user: User, db: Session) -> Capsule:
    capsule = db.scalar(select(Capsule).where(
        Capsule.public_id == public_id, Capsule.owner_id == user.id
    ))
    if capsule is None or not _readable(capsule):
        raise HTTPException(404, "Not found")
    return capsule


@router.get("/{public_id}")
def get_capsule(public_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    capsule = _owned_readable(public_id, user, db)
    return {
        "id": capsule.public_id,
        "year": capsule.year,
        "content_type": capsule.content_type,
        "body": capsule.body,
        "opened_at": capsule.opened_at.isoformat() if capsule.opened_at else None,
    }


@router.post("/{public_id}/open", dependencies=[Depends(csrf_protect)])
def open_capsule(public_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    capsule = _owned_readable(public_id, user, db)
    if capsule.opened_at is None:
        capsule.opened_at = datetime.now(timezone.utc)
        db.add(capsule)
        db.commit()
    return {"id": capsule.public_id, "state": "opened"}
