from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, UTCDateTime
from app.security import new_entry_slug, new_public_id


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Friend(Base):
    """An account. Administrators are accounts with is_admin set."""

    __tablename__ = "friends"
    __table_args__ = (
        CheckConstraint("birth_month BETWEEN 1 AND 12", name="ck_friends_birth_month"),
        CheckConstraint("birth_day BETWEEN 1 AND 31", name="ck_friends_birth_day"),
        CheckConstraint("leap_day_policy IN ('feb28', 'mar1')", name="ck_friends_leap_policy"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, default=new_public_id)
    entry_slug: Mapped[str] = mapped_column(String(48), unique=True, default=new_entry_slug)
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(255))
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    timezone: Mapped[str] = mapped_column(String(64))
    birth_month: Mapped[int] = mapped_column(Integer)
    birth_day: Mapped[int] = mapped_column(Integer)
    leap_day_policy: Mapped[str] = mapped_column(String(8), default="feb28")

    theme_key: Mapped[str] = mapped_column(String(32))
    theme_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_utcnow)


class AuthSession(Base):
    """A login session. Only a hash of the cookie token is stored."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    friend_id: Mapped[int] = mapped_column(ForeignKey("friends.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class Capsule(Base):
    """One yearly birthday capsule.

    The gift itself lives in CapsuleContent so that listing queries can never touch it.
    """

    __tablename__ = "capsules"
    __table_args__ = (
        UniqueConstraint("friend_id", "edition_year", name="uq_capsules_friend_year"),
        CheckConstraint("state IN ('draft', 'published')", name="ck_capsules_state"),
        Index("ix_capsules_friend_unlock", "friend_id", "unlock_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, default=new_public_id)
    friend_id: Mapped[int] = mapped_column(ForeignKey("friends.id", ondelete="CASCADE"))
    edition_year: Mapped[int] = mapped_column(Integer)
    unlock_at: Mapped[datetime] = mapped_column(UTCDateTime)
    content_type: Mapped[str] = mapped_column(String(32))
    state: Mapped[str] = mapped_column(String(16), default="draft")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_utcnow)
    opened_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class CapsuleContent(Base):
    __tablename__ = "capsule_contents"

    capsule_id: Mapped[int] = mapped_column(
        ForeignKey("capsules.id", ondelete="CASCADE"), primary_key=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class LoginAttempt(Base):
    """Failed login or password-change attempts, keyed by a hash so raw values are not stored."""

    __tablename__ = "login_attempts"
    __table_args__ = (Index("ix_login_attempts_key_time", "key_hash", "attempted_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key_hash: Mapped[str] = mapped_column(String(64))
    attempted_at: Mapped[datetime] = mapped_column(UTCDateTime)
