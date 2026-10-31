"""Request dependencies: settings, clock, and the authentication/authorization chain.

Chain: current_context (valid session, CSRF on unsafe methods) -> active_user (password already
changed) -> admin_user. Account identity always comes from the session cookie, never from an
identifier the browser supplies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.models import AuthSession, Friend
from app.security import csrf_token_for, hash_token, tokens_match

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
LAST_SEEN_GRANULARITY = timedelta(minutes=1)


def get_settings_dep(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_now(request: Request) -> datetime:
    """Server time. The browser clock is never consulted."""
    now: datetime = request.app.state.clock()
    return now


DbDep = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
NowDep = Annotated[datetime, Depends(get_now)]


def client_ip(request: Request, settings: Settings) -> str:
    if settings.trust_forwarded_for:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # Rightmost entry: the one appended by our own trusted proxy.
            return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


@dataclass
class AuthContext:
    friend: Friend
    session: AuthSession
    token: str


def current_context(request: Request, db: DbDep, settings: SettingsDep, now: NowDep) -> AuthContext:
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    row = db.execute(
        select(AuthSession).where(AuthSession.token_hash == hash_token(token))
    ).scalar_one_or_none()
    if row is None or row.revoked_at is not None or row.expires_at <= now:
        raise HTTPException(status_code=401, detail="Not authenticated")
    friend = db.get(Friend, row.friend_id)
    if friend is None or not friend.is_active:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if request.method not in SAFE_METHODS:
        supplied = request.headers.get("x-csrf-token", "")
        expected = csrf_token_for(token, settings.secret_key.get_secret_value())
        if not supplied or not tokens_match(supplied, expected):
            raise HTTPException(status_code=403, detail="CSRF check failed")

    if now - row.last_seen_at >= LAST_SEEN_GRANULARITY:
        row.last_seen_at = now
        db.commit()
    return AuthContext(friend=friend, session=row, token=token)


ContextDep = Annotated[AuthContext, Depends(current_context)]


def active_user(ctx: ContextDep) -> AuthContext:
    if ctx.friend.must_change_password:
        raise HTTPException(status_code=403, detail="password_change_required")
    return ctx


ActiveDep = Annotated[AuthContext, Depends(active_user)]


def admin_user(ctx: ActiveDep) -> AuthContext:
    if not ctx.friend.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    return ctx


AdminDep = Annotated[AuthContext, Depends(admin_user)]
