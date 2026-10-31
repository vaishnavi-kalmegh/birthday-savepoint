"""Theme configuration. Stored per friend in the database and validated on every write.

Adding a theme means adding a key here and a scene on the frontend; no per-friend code.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# "archive" is the neutral scene shown for an unknown or inactive entry link. It cannot be
# assigned to a friend.
FALLBACK_THEME_KEY = "archive"
ASSIGNABLE_THEME_KEYS: frozenset[str] = frozenset({"rooftop"})

HexColor = Field(pattern=r"^#[0-9a-fA-F]{6}$")

Ambient = Literal["rain", "stars", "dust", "none"]


class ThemeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accent: str = HexColor
    accent_alt: str = HexColor
    ambient: Ambient = "stars"
    greeting: str | None = Field(default=None, max_length=120)


DEFAULT_THEME_CONFIGS: dict[str, dict[str, Any]] = {
    "rooftop": {"accent": "#e0414f", "accent_alt": "#3d7bd9", "ambient": "rain"},
}

FALLBACK_THEME_CONFIG: dict[str, Any] = {
    "accent": "#7a8cff",
    "accent_alt": "#3b4560",
    "ambient": "stars",
    "greeting": None,
}


def validate_theme(theme_key: str, config: dict[str, Any] | None) -> dict[str, Any]:
    if theme_key not in ASSIGNABLE_THEME_KEYS:
        raise ValueError(f"unknown theme: {theme_key!r}")
    merged = {**DEFAULT_THEME_CONFIGS[theme_key], **(config or {})}
    return ThemeConfig(**merged).model_dump()
