from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import csrf_protect, current_user
from ..models import Capsule, User
from ..timelock import as_utc, is_unlocked

router = APIRouter(prefix="/api/capsules", tags=["capsules"])


def _readable(capsule: Capsule) -> bool:
    return capsule.published and is_unlocked(capsule.unlock_at)


@router.get("")
def list_capsules(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Capsule).where(Capsule.owner_id == user.id).order_by(Capsule.year)
    ).all()
    result = []
    for capsule in rows:
        if not _readable(capsule):
            result.append({
                "id": capsule.public_id,
                "year": capsule.year,
                "state": "sealed",
                "unlock_at": as_utc(capsule.unlock_at).isoformat(),
            })
        else:
            result.append({
                "id": capsule.public_id,
                "year": capsule.year,
                "state": "opened" if capsule.opened_at else "available",
                "unlock_at": as_utc(capsule.unlock_at).isoformat(),
                "content_type": capsule.content_type,
            })
    return result


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
