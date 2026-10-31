from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import AuthSession, Friend
from app.security import (
    hash_password,
    hash_token,
    new_session_token,
    password_needs_rehash,
    verify_password,
)


def find_active_friend_by_slug(db: Session, entry_slug: str) -> Friend | None:
    return db.execute(
        select(Friend).where(Friend.entry_slug == entry_slug, Friend.is_active.is_(True))
    ).scalar_one_or_none()


def check_credentials(db: Session, entry_slug: str, password: str) -> Friend | None:
    """Return the friend if the slug and password match an active account, else None.

    The same amount of hashing work happens either way.
    """
    friend = find_active_friend_by_slug(db, entry_slug)
    if not verify_password(friend.password_hash if friend else None, password):
        return None
    assert friend is not None
    if password_needs_rehash(friend.password_hash):
        friend.password_hash = hash_password(password)
        db.commit()
    return friend


def create_session(
    db: Session, friend: Friend, *, now: datetime, settings: Settings
) -> tuple[str, AuthSession]:
    """Create a session and return (raw cookie token, row). Only the token's hash is stored."""
    ttl_hours = settings.admin_session_ttl_hours if friend.is_admin else settings.session_ttl_hours
    token = new_session_token()
    row = AuthSession(
        token_hash=hash_token(token),
        friend_id=friend.id,
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(hours=ttl_hours),
    )
    db.add(row)
    db.commit()
    return token, row


def revoke_session(db: Session, session_row: AuthSession, *, now: datetime) -> None:
    session_row.revoked_at = now
    db.commit()


def revoke_all_sessions(
    db: Session, friend_id: int, *, now: datetime, except_session_id: int | None = None
) -> None:
    stmt = (
        update(AuthSession)
        .where(AuthSession.friend_id == friend_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    if except_session_id is not None:
        stmt = stmt.where(AuthSession.id != except_session_id)
    db.execute(stmt)
    db.commit()


def set_password(db: Session, friend: Friend, new_password: str, *, must_change: bool) -> None:
    friend.password_hash = hash_password(new_password)
    friend.must_change_password = must_change
    db.commit()
