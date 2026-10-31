"""Minimal administrator routes. The full admin panel is a later milestone; these exist so the
admin boundary and session revocation are real and tested from the start."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select

from app.deps import AdminDep, DbDep, NowDep
from app.models import Friend
from app.schemas import AdminFriend
from app.services import auth as auth_service
from app.services import friends as friend_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/friends", response_model=list[AdminFriend])
def list_friends(_admin: AdminDep, db: DbDep) -> list[AdminFriend]:
    rows = db.execute(select(Friend).order_by(Friend.display_name)).scalars()
    return [
        AdminFriend(
            id=f.public_id, display_name=f.display_name, is_active=f.is_active, is_admin=f.is_admin
        )
        for f in rows
    ]


@router.post("/friends/{public_id}/revoke-sessions", status_code=204)
def revoke_sessions(public_id: str, _admin: AdminDep, db: DbDep, now: NowDep) -> Response:
    friend = friend_service.get_by_public_id(db, public_id)
    if friend is None:
        raise HTTPException(status_code=404, detail="Not found")
    auth_service.revoke_all_sessions(db, friend.id, now=now)
    return Response(status_code=204)
