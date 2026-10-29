import json
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import csrf_protect, require_admin
from ..models import AuthSession, Capsule, User
from ..security import hash_password
from ..timelock import unlock_moment

router = APIRouter(
    prefix="/api/admin", tags=["admin"],
    dependencies=[Depends(require_admin), Depends(csrf_protect)],
)


class FriendIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    login_id: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=256)
    display_name: str = Field(min_length=1, max_length=80)
    birth_month: int = Field(ge=1, le=12)
    birth_day: int = Field(ge=1, le=31)
    timezone: str = Field(default="UTC", max_length=64)
    theme: dict[str, Any] = Field(default_factory=dict)

    @field_validator("theme")
    @classmethod
    def theme_must_be_small_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError):
            raise ValueError("theme must contain JSON-compatible values")
        if len(encoded) > 8192:
            raise ValueError("theme must be at most 8192 bytes")
        return value


class LetterBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=20_000)
    title: str | None = Field(default=None, max_length=120)


class CapsuleIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    year: int = Field(ge=2000, le=2200)
    content_type: str = Field(pattern=r"^letter$")
    body: LetterBody
    published: bool = False


@router.post("/friends", status_code=201)
def create_friend(body: FriendIn, db: Session = Depends(get_db)):
    try:
        ZoneInfo(body.timezone)
        datetime(2024, body.birth_month, body.birth_day)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(422, "Invalid timezone or birthday")
    user = User(
        login_id=body.login_id,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        birth_month=body.birth_month,
        birth_day=body.birth_day,
        timezone=body.timezone,
        theme=body.theme,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "login_id already in use")
    return {"public_id": user.public_id}


@router.post("/friends/{public_id}/capsules", status_code=201)
def create_capsule(public_id: str, body: CapsuleIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.public_id == public_id))
    if user is None:
        raise HTTPException(404, "Not found")
    capsule = Capsule(
        owner_id=user.id, year=body.year, content_type=body.content_type,
        body=body.body.model_dump(exclude_none=True), published=body.published,
        unlock_at=unlock_moment(user.birth_month, user.birth_day, body.year, user.timezone),
    )
    db.add(capsule)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A capsule for that year already exists")
    return {"id": capsule.public_id}


@router.post("/friends/{public_id}/disable")
def disable_friend(
    public_id: str,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.public_id == public_id))
    if user is None:
        raise HTTPException(404, "Not found")
    if user.id == actor.id:
        raise HTTPException(400, "The active admin cannot disable their own account")
    user.is_active = False
    now = datetime.now(timezone.utc)
    sessions = db.scalars(select(AuthSession).where(
        AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)
    ))
    for session in sessions:
        session.revoked_at = now
    db.commit()
    return {"ok": True}
