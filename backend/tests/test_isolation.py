"""Cross-account isolation, unauthenticated access, enumeration, and the admin boundary."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models import Capsule

COOKIE = "sp_session"

PROTECTED = [
    ("GET", "/api/me"),
    ("GET", "/api/capsules"),
    ("GET", "/api/capsules/some-id"),
    ("POST", "/api/capsules/some-id/open"),
    ("POST", "/api/auth/logout"),
    ("POST", "/api/auth/change-password"),
    ("GET", "/api/admin/friends"),
    ("POST", "/api/admin/friends/some-id/revoke-sessions"),
]


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_unauthenticated_visitors_cannot_reach_protected_routes(client, method, path) -> None:
    response = client.request(method, path, json={} if method == "POST" else None)
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_garbage_or_forged_session_cookies_are_rejected(client, method, path) -> None:
    client.cookies.set(COOKIE, "forged-token-value", domain="testserver")
    response = client.request(method, path, json={} if method == "POST" else None)
    assert response.status_code == 401


def test_friend_cannot_read_another_friends_capsule_by_id(
    client, make_client, make_friend, make_capsule, login, clock
) -> None:
    a, b = make_friend("Demo A"), make_friend("Demo B")
    capsule_b, marker_b = make_capsule(b, 2026)  # unlocked, published, owned by B
    login(client, a)

    forged = client.get(f"/api/capsules/{capsule_b.public_id}")
    nonexistent = client.get("/api/capsules/aaaaaaaaaaaaaaaa")
    assert forged.status_code == 404
    assert forged.status_code == nonexistent.status_code
    assert forged.json() == nonexistent.json()  # cannot tell "someone else's" from "does not exist"
    assert marker_b not in forged.text

    # The legitimate owner still gets it.
    owner = make_client()
    login(owner, b)
    assert owner.get(f"/api/capsules/{capsule_b.public_id}").status_code == 200


def test_friend_cannot_open_or_modify_another_friends_capsule(
    client, make_client, make_friend, make_capsule, login, db: Session
) -> None:
    a, b = make_friend("Demo A"), make_friend("Demo B")
    capsule_b, _ = make_capsule(b, 2026)
    csrf_a = login(client, a)

    response = client.post(
        f"/api/capsules/{capsule_b.public_id}/open", headers={"X-CSRF-Token": csrf_a}
    )
    assert response.status_code == 404
    fresh = db.get(Capsule, capsule_b.id)
    db.refresh(fresh)
    assert fresh.opened_at is None  # B's capsule was not marked opened by A


def test_archive_contains_only_the_callers_capsules(
    client, make_friend, make_capsule, login
) -> None:
    a, b = make_friend("Demo A"), make_friend("Demo B")
    capsule_a, marker_a = make_capsule(a, 2026)
    capsule_b, marker_b = make_capsule(b, 2026)
    login(client, a)

    response = client.get("/api/capsules")
    ids = [c["id"] for c in response.json()["capsules"]]
    assert ids == [capsule_a.public_id]
    assert capsule_b.public_id not in response.text
    assert marker_b not in response.text


def test_identity_is_taken_from_the_session_not_from_request_values(
    client, make_friend, make_capsule, login
) -> None:
    a, b = make_friend("Demo A"), make_friend("Demo B")
    capsule_b, marker_b = make_capsule(b, 2026)
    login(client, a)

    me = client.get(
        "/api/me",
        params={"id": b.friend.public_id, "friend_id": b.friend.id, "user": "Demo B"},
        headers={"X-User-Id": str(b.friend.id), "X-Friend-Id": b.friend.public_id},
    )
    assert me.json()["display_name"] == "Demo A"

    archive = client.get(
        "/api/capsules", params={"friend_id": b.friend.id, "owner": b.friend.public_id}
    )
    assert marker_b not in archive.text
    assert capsule_b.public_id not in archive.text


@pytest.mark.parametrize(
    "path",
    [
        "/api/friends",
        "/api/users",
        "/api/accounts",
        "/api/capsules/all",
        "/api/themes",
        "/api/stats",
    ],
)
def test_no_public_endpoint_lists_accounts_or_counts_them(client, make_friend, path) -> None:
    make_friend("Demo A")
    make_friend("Demo B")
    response = client.get(path)
    assert response.status_code in (401, 404, 405)
    assert "Demo A" not in response.text and "Demo B" not in response.text


def test_entry_link_responses_reveal_nothing_about_which_accounts_exist(
    client, make_friend, db: Session
) -> None:
    live, retired = make_friend("Demo Live"), make_friend("Demo Retired")
    retired.friend.is_active = False
    db.commit()

    unknown_one = client.get("/api/entry/" + "u" * 22).json()
    unknown_two = client.get("/api/entry/" + "v" * 22).json()
    deactivated = client.get(f"/api/entry/{retired.friend.entry_slug}").json()
    valid = client.get(f"/api/entry/{live.friend.entry_slug}").json()

    assert unknown_one == unknown_two == deactivated  # same neutral scene
    assert set(valid) == {"key", "accent", "accent_alt", "ambient"}  # theme only
    text = str(valid)
    assert "Demo" not in text and live.friend.public_id not in text


def test_entry_link_alone_grants_no_access(client, make_friend) -> None:
    account = make_friend()
    client.get(f"/api/entry/{account.friend.entry_slug}")
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/capsules").status_code == 401


def test_ordinary_users_cannot_use_admin_routes(client, make_client, make_friend, login) -> None:
    friend, other = make_friend("Demo Friend"), make_friend("Demo Other")
    csrf = login(client, friend)

    assert client.get("/api/admin/friends").status_code == 403
    revoke = client.post(
        f"/api/admin/friends/{other.friend.public_id}/revoke-sessions",
        headers={"X-CSRF-Token": csrf},
    )
    assert revoke.status_code == 403

    # The attempt had no effect: the other account's session is untouched.
    other_client = make_client()
    login(other_client, other)
    client.post(
        f"/api/admin/friends/{other.friend.public_id}/revoke-sessions",
        headers={"X-CSRF-Token": csrf},
    )
    assert other_client.get("/api/me").status_code == 200


def test_admin_can_list_accounts_and_revoke_sessions(
    client, make_client, make_friend, login
) -> None:
    admin = make_friend("Demo Admin", admin=True)
    friend = make_friend("Demo Friend")
    friend_client = make_client()
    login(friend_client, friend)
    csrf = login(client, admin)

    listing = client.get("/api/admin/friends")
    assert listing.status_code == 200
    assert {f["display_name"] for f in listing.json()} == {"Demo Admin", "Demo Friend"}

    assert friend_client.get("/api/me").status_code == 200
    revoke = client.post(
        f"/api/admin/friends/{friend.friend.public_id}/revoke-sessions",
        headers={"X-CSRF-Token": csrf},
    )
    assert revoke.status_code == 204
    assert friend_client.get("/api/me").status_code == 401  # revoked session no longer works

    missing = client.post(
        "/api/admin/friends/does-not-exist/revoke-sessions", headers={"X-CSRF-Token": csrf}
    )
    assert missing.status_code == 404


def test_admin_routes_still_require_csrf(client, make_friend, login) -> None:
    admin = make_friend("Demo Admin", admin=True)
    other = make_friend("Demo Friend")
    login(client, admin)
    response = client.post(f"/api/admin/friends/{other.friend.public_id}/revoke-sessions")
    assert response.status_code == 403


def test_admin_who_has_not_changed_their_one_time_password_is_blocked(
    client, make_friend, login
) -> None:
    admin = make_friend("Demo Admin", admin=True, ready=False)
    login(client, admin)
    assert client.get("/api/admin/friends").status_code == 403
