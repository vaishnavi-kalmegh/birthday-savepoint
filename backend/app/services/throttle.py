"""Failed-attempt throttling stored in the database, so limits survive restarts and are shared
between worker processes."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import LoginAttempt


def failure_count(db: Session, key_hash: str, *, now: datetime, window: timedelta) -> int:
    stmt = (
        select(func.count())
        .select_from(LoginAttempt)
        .where(LoginAttempt.key_hash == key_hash, LoginAttempt.attempted_at > now - window)
    )
    return int(db.execute(stmt).scalar_one())


def record_failure(db: Session, key_hashes: list[str], *, now: datetime, window: timedelta) -> None:
    for key_hash in key_hashes:
        db.add(LoginAttempt(key_hash=key_hash, attempted_at=now))
    # Opportunistic cleanup keeps the table small without a separate job.
    db.execute(delete(LoginAttempt).where(LoginAttempt.attempted_at < now - window * 4))
    db.commit()


def clear_failures(db: Session, key_hash: str) -> None:
    db.execute(delete(LoginAttempt).where(LoginAttempt.key_hash == key_hash))
    db.commit()
