import hmac
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .db import get_db
from .models import AuthSession, User
from .security import sha256
from .timelock import as_utc


def current_session(request: Request, db: Session = Depends(get_db)) -> AuthSession:
    token = request.cookies.get(config.COOKIE_NAME)
    if not token:
        raise HTTPException(401, "Not authenticated")
    s = db.scalar(select(AuthSession).where(AuthSession.token_hash == sha256(token)))
    if s is None or s.revoked_at is not None or as_utc(s.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(401, "Not authenticated")
    return s


def current_user(s: AuthSession = Depends(current_session), db: Session = Depends(get_db)) -> User:
    user = db.get(User, s.user_id)
    if user is None or not user.is_active:
        raise HTTPException(401, "Not authenticated")
    return user


def csrf_protect(request: Request, s: AuthSession = Depends(current_session)) -> None:
    sent = request.headers.get("x-csrf-token", "")
    if not hmac.compare_digest(sha256(sent), s.csrf_hash):
        raise HTTPException(403, "Invalid CSRF token")


def require_admin(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(404, "Not found")
    return user
