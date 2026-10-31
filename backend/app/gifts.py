"""Gift types. Each type has a Pydantic payload model; the registry makes new types additive.

Only "letter" exists today. A new type is one model plus one registry entry here, a renderer on
the frontend, and (for media-backed types) an authorization-aware media route.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LetterPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    greeting: str | None = Field(default=None, max_length=120)
    paragraphs: list[str] = Field(min_length=1, max_length=80)
    signoff: str | None = Field(default=None, max_length=120)
    postscript: str | None = Field(default=None, max_length=2000)

    def model_post_init(self, __context: Any) -> None:
        if any(not p.strip() or len(p) > 6000 for p in self.paragraphs):
            raise ValueError("paragraphs must be non-empty and at most 6000 characters")


GIFT_TYPES: dict[str, type[BaseModel]] = {"letter": LetterPayload}


def validate_gift(content_type: str, raw: dict[str, Any]) -> dict[str, Any]:
    """Validate a payload for storage."""
    model = GIFT_TYPES.get(content_type)
    if model is None:
        raise ValueError(f"unknown gift type: {content_type!r}")
    return model(**raw).model_dump()


def render_gift(content_type: str, raw: dict[str, Any]) -> dict[str, Any]:
    """Re-validate stored data on the way out so malformed rows never reach a client."""
    return validate_gift(content_type, raw)
