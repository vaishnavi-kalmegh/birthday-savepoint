from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Request bodies reject unknown fields, so a client cannot smuggle in extra values."""

    model_config = ConfigDict(extra="forbid")


class LoginRequest(StrictModel):
    entry_slug: str = Field(min_length=8, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(StrictModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class LoginResponse(BaseModel):
    csrf_token: str
    must_change_password: bool


class EntryTheme(BaseModel):
    """What the pre-login scene needs. Deliberately contains no name, date, or account data."""

    key: str
    accent: str
    accent_alt: str
    ambient: str


class ThemeOut(EntryTheme):
    greeting: str | None


class MeResponse(BaseModel):
    display_name: str
    timezone: str
    theme: ThemeOut
    csrf_token: str
    must_change_password: bool


class CapsuleSummary(BaseModel):
    id: str
    edition_year: int
    unlock_at: datetime
    opened_at: datetime | None
    gift_type: str


class SealedSlot(BaseModel):
    """The next capsule, shown sealed. It carries no id, type, or content, and says nothing
    about whether a gift has been prepared."""

    edition_year: int
    unlock_at: datetime


class ArchiveResponse(BaseModel):
    capsules: list[CapsuleSummary]
    next_sealed: SealedSlot
    server_time: datetime


class GiftOut(BaseModel):
    type: str
    data: dict[str, Any]


class CapsuleDetail(CapsuleSummary):
    gift: GiftOut


class AdminFriend(BaseModel):
    id: str
    display_name: str
    is_active: bool
    is_admin: bool
