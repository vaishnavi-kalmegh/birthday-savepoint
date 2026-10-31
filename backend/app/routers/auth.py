from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request, Response

from app.deps import ContextDep, DbDep, NowDep, SettingsDep, client_ip
from app.schemas import ChangePasswordRequest, EntryTheme, LoginRequest, LoginResponse
from app.security import csrf_token_for, hash_lookup_key, verify_password
from app.services import auth as auth_service
from app.services import throttle
from app.themes import FALLBACK_THEME_CONFIG, FALLBACK_THEME_KEY

router = APIRouter(prefix="/api", tags=["auth"])

_FALLBACK_ENTRY = EntryTheme(
    key=FALLBACK_THEME_KEY, **{k: v for k, v in FALLBACK_THEME_CONFIG.items() if k != "greeting"}
)


def _too_many(window: timedelta) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail="Too many attempts. Try again later.",
        headers={"Retry-After": str(int(window.total_seconds()))},
    )


@router.get("/entry/{entry_slug}", response_model=EntryTheme)
def entry(entry_slug: str, db: DbDep) -> EntryTheme:
    """Theme for the personal entry link. An unknown, malformed, or deactivated link gets the
    same neutral scene with the same shape, so the response does not confirm that an account
    exists. Possessing the link grants no access to anything private."""
    friend = auth_service.find_active_friend_by_slug(db, entry_slug[:64])
    if friend is None:
        return _FALLBACK_ENTRY
    cfg = friend.theme_config
    return EntryTheme(
        key=friend.theme_key,
        accent=cfg["accent"],
        accent_alt=cfg["accent_alt"],
        ambient=cfg["ambient"],
    )


@router.post("/auth/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: DbDep,
    settings: SettingsDep,
    now: NowDep,
) -> LoginResponse:
    window = timedelta(minutes=settings.login_window_minutes)
    account_key = hash_lookup_key("acct", body.entry_slug)
    ip_key = hash_lookup_key("ip", client_ip(request, settings))

    if (
        throttle.failure_count(db, account_key, now=now, window=window)
        >= settings.login_max_failures_per_account
        or throttle.failure_count(db, ip_key, now=now, window=window)
        >= settings.login_max_failures_per_ip
    ):
        raise _too_many(window)

    friend = auth_service.check_credentials(db, body.entry_slug, body.password)
    if friend is None:
        throttle.record_failure(db, [account_key, ip_key], now=now, window=window)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    throttle.clear_failures(db, account_key)
    token, _row = auth_service.create_session(db, friend, now=now, settings=settings)
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=int(
            timedelta(
                hours=settings.admin_session_ttl_hours
                if friend.is_admin
                else settings.session_ttl_hours
            ).total_seconds()
        ),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return LoginResponse(
        csrf_token=csrf_token_for(token, settings.secret_key.get_secret_value()),
        must_change_password=friend.must_change_password,
    )


@router.post("/auth/logout", status_code=204)
def logout(
    ctx: ContextDep, response: Response, db: DbDep, settings: SettingsDep, now: NowDep
) -> Response:
    auth_service.revoke_session(db, ctx.session, now=now)
    response.delete_cookie(settings.cookie_name, path="/")
    response.status_code = 204
    return response


@router.post("/auth/change-password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    ctx: ContextDep,
    db: DbDep,
    settings: SettingsDep,
    now: NowDep,
) -> Response:
    window = timedelta(minutes=settings.login_window_minutes)
    key = hash_lookup_key("pw", ctx.friend.public_id)
    if (
        throttle.failure_count(db, key, now=now, window=window)
        >= settings.login_max_failures_per_account
    ):
        raise _too_many(window)
    if not verify_password(ctx.friend.password_hash, body.current_password):
        throttle.record_failure(db, [key], now=now, window=window)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if body.new_password == body.current_password:
        raise HTTPException(status_code=422, detail="New password must be different")

    auth_service.set_password(db, ctx.friend, body.new_password, must_change=False)
    auth_service.revoke_all_sessions(db, ctx.friend.id, now=now, except_session_id=ctx.session.id)
    throttle.clear_failures(db, key)
    return Response(status_code=204)
