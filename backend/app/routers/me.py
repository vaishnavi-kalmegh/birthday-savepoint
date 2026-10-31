from __future__ import annotations

from fastapi import APIRouter

from app.deps import ContextDep, SettingsDep
from app.schemas import MeResponse, ThemeOut
from app.security import csrf_token_for

router = APIRouter(prefix="/api", tags=["me"])


@router.get("/me", response_model=MeResponse)
def me(ctx: ContextDep, settings: SettingsDep) -> MeResponse:
    """The caller's own profile. Identity comes from the session, never from a request value."""
    friend = ctx.friend
    return MeResponse(
        display_name=friend.display_name,
        timezone=friend.timezone,
        theme=ThemeOut(key=friend.theme_key, **friend.theme_config),
        csrf_token=csrf_token_for(ctx.token, settings.secret_key.get_secret_value()),
        must_change_password=friend.must_change_password,
    )
