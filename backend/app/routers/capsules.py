from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.deps import ActiveDep, DbDep, NowDep
from app.models import Capsule
from app.schemas import ArchiveResponse, CapsuleDetail, CapsuleSummary, GiftOut, SealedSlot
from app.services import capsules as capsule_service

router = APIRouter(prefix="/api/capsules", tags=["capsules"])

# One response for every reason a capsule is unavailable: it does not exist, belongs to someone
# else, is not yet unlocked, or is not published. The caller cannot tell these apart.
_NOT_FOUND = HTTPException(status_code=404, detail="Not found")


def _summary(capsule: Capsule) -> CapsuleSummary:
    return CapsuleSummary(
        id=capsule.public_id,
        edition_year=capsule.edition_year,
        unlock_at=capsule.unlock_at,
        opened_at=capsule.opened_at,
        gift_type=capsule.content_type,
    )


@router.get("", response_model=ArchiveResponse)
def archive(ctx: ActiveDep, db: DbDep, now: NowDep) -> ArchiveResponse:
    visible = capsule_service.list_visible(db, ctx.friend, now=now)
    year, unlock_at = capsule_service.next_sealed(ctx.friend, now=now)
    return ArchiveResponse(
        capsules=[_summary(c) for c in visible],
        next_sealed=SealedSlot(edition_year=year, unlock_at=unlock_at),
        server_time=now,
    )


@router.get("/{capsule_id}", response_model=CapsuleDetail)
def read_capsule(capsule_id: str, ctx: ActiveDep, db: DbDep, now: NowDep) -> CapsuleDetail:
    capsule = capsule_service.get_visible(db, ctx.friend, capsule_id, now=now)
    if capsule is None:
        raise _NOT_FOUND
    gift = capsule_service.load_gift(db, capsule)
    return CapsuleDetail(**_summary(capsule).model_dump(), gift=GiftOut(**gift))


@router.post("/{capsule_id}/open", response_model=CapsuleDetail)
def open_capsule(capsule_id: str, ctx: ActiveDep, db: DbDep, now: NowDep) -> CapsuleDetail:
    """Record that the owner opened the capsule (idempotent) and return the gift."""
    capsule = capsule_service.get_visible(db, ctx.friend, capsule_id, now=now)
    if capsule is None:
        raise _NOT_FOUND
    capsule_service.mark_opened(db, capsule, now=now)
    gift = capsule_service.load_gift(db, capsule)
    return CapsuleDetail(**_summary(capsule).model_dump(), gift=GiftOut(**gift))
