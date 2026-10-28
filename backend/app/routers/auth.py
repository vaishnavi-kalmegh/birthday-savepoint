from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config, ratelimit
from ..db import get_db
from ..deps import csrf_protect, current_session, current_user
from ..models import AuthSession, User
from ..security import new_token, sha256, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    login_id: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "?"
    keys = [f"id:{body.login_id.lower()}", f"ip:{ip}"]
    if any(ratelimit.is_blocked(key) for key in keys):
        raise HTTPException(429, "Too many attempts. Try again later.")

    user = db.scalar(select(User).where(User.login_id == body.login_id.lower()))
    ok = verify_password(user.password_hash if user else None, body.password)
    if not ok or user is None or not user.is_active:
        for key in keys:
            ratelimit.record_failure(key)
        raise HTTPException(401, "Invalid credentials")

    # Clear both counters after successful authentication.
    for key in keys:
        ratelimit.reset(key)
    token, csrf = new_token(), new_token()
    db.add(AuthSession(
        user_id=user.id,
        token_hash=sha256(token),
        csrf_hash=sha256(csrf),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=config.SESSION_TTL_HOURS),
    ))
    db.commit()
    response.set_cookie(
        config.COOKIE_NAME, token, httponly=True, secure=config.COOKIE_SECURE,
        samesite="strict", max_age=config.SESSION_TTL_HOURS * 3600, path="/",
    )
    return {"csrf_token": csrf}


@router.post("/logout", dependencies=[Depends(csrf_protect)])
def logout(response: Response, s: AuthSession = Depends(current_session), db: Session = Depends(get_db)):
    s.revoked_at = datetime.now(timezone.utc)
    db.add(s)
    db.commit()
    response.delete_cookie(config.COOKIE_NAME, path="/")
    return {"ok": True}


@router.post("/csrf")
def refresh_csrf(
    s: AuthSession = Depends(current_session),
    db: Session = Depends(get_db),
):
    # Bootstrap a CSRF token after a page reload. This endpoint requires the
    # existing SameSite=Strict session cookie and returns the token only in its
    # response body; the token itself is never stored in browser local storage.
    csrf = new_token()
    s.csrf_hash = sha256(csrf)
    db.add(s)
    db.commit()
    return {"csrf_token": csrf}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"display_name": user.display_name, "theme": user.theme}
