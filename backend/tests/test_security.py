from types import SimpleNamespace

import pytest
from sqlalchemy import select
from starlette.requests import Request

from app.deps import csrf_protect
from app.models import User
from .conftest import PW, login, make_client


def test_1_cannot_read_other_friends_capsule_by_changing_id(world):
    client = make_client()
    login(client, "alice")
    response = client.get(f"/api/capsules/{world['ids']['bob']['past']}")
    assert response.status_code == 404
    assert client.get("/api/capsules/" + "0" * 32).status_code == 404
    listed = {
        item["id"] for item in client.get("/api/capsules").json() if "id" in item
    }
    assert world["ids"]["bob"]["past"] not in listed


def test_1b_cannot_open_other_friends_capsule(world):
    client = make_client()
    headers = login(client, "alice")
    assert client.post(
        f"/api/capsules/{world['ids']['bob']['past']}/open", headers=headers
    ).status_code == 404


def test_2_unauthenticated_gets_nothing(world):
    client = make_client()
    assert client.get("/api/capsules").status_code == 401
    assert client.get(f"/api/capsules/{world['ids']['alice']['past']}").status_code == 401
    assert client.get("/api/auth/me").status_code == 401


def test_3_future_capsule_reveals_nothing(world):
    client = make_client()
    login(client, "alice")
    future_id = world["ids"]["alice"]["future"]
    assert client.get(f"/api/capsules/{future_id}").status_code == 404
    listing = client.get("/api/capsules")
    assert "SECRET" not in listing.text
    assert future_id not in listing.text
    sealed = [item for item in listing.json() if item["state"] == "sealed"]
    assert len(sealed) == 1
    assert set(sealed[0]) == {"year", "state", "unlock_at"}
    assert sealed[0]["year"] != 2199


def test_3b_past_capsule_readable_and_open_is_idempotent(world):
    client = make_client()
    headers = login(client, "alice")
    public_id = world["ids"]["alice"]["past"]
    assert client.get(f"/api/capsules/{public_id}").json()["body"]["text"] == "alice-past"
    assert client.post(f"/api/capsules/{public_id}/open", headers=headers).status_code == 200
    first_opened_at = client.get(f"/api/capsules/{public_id}").json()["opened_at"]
    client.post(f"/api/capsules/{public_id}/open", headers=headers)
    assert client.get(f"/api/capsules/{public_id}").json()["opened_at"] == first_opened_at


def test_3c_unpublished_capsule_is_hidden_even_after_unlock(world):
    admin = world["admin"]
    response = admin.post(
        f"/api/admin/friends/{world['ids']['alice']['pid']}/capsules",
        headers=world["admin_h"],
        json={"year": 2002, "content_type": "letter", "body": {"text": "draft"}, "published": False},
    )
    client = make_client()
    login(client, "alice")
    assert client.get(f"/api/capsules/{response.json()['id']}").status_code == 404
    assert response.json()["id"] not in client.get("/api/capsules").text


def test_4_no_endpoint_enumerates_users(world):
    client = make_client()
    login(client, "alice")
    for path in ("/api/users", "/api/friends", "/api/admin/friends", "/api/auth/users"):
        assert client.get(path).status_code in (404, 405)
    assert set(client.get("/api/auth/me").json()) == {"display_name", "theme", "is_admin"}


def test_4b_login_errors_do_not_reveal_which_accounts_exist(world):
    client = make_client()
    unknown = client.post("/api/auth/login", json={"login_id": "nobody", "password": "x" * 12})
    wrong = client.post("/api/auth/login", json={"login_id": "alice", "password": "x" * 12})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


def test_5_non_admin_cannot_use_admin_functions(world):
    client = make_client()
    headers = login(client, "alice")
    response = client.post("/api/admin/friends", headers=headers, json={
        "login_id": "mallory", "password": PW, "display_name": "M",
        "birth_month": 1, "birth_day": 1,
    })
    assert response.status_code == 404
    response = client.post(
        f"/api/admin/friends/{world['ids']['bob']['pid']}/disable", headers=headers
    )
    assert response.status_code == 404
    assert make_client().post("/api/admin/friends", json={}).status_code == 401


def test_6_private_media_placeholder():
    pytest.skip("No media endpoints exist yet; add authorization tests when they do.")


def test_7_logout_and_disable_revoke_access(world):
    client = make_client()
    headers = login(client, "alice")
    assert client.get("/api/capsules").status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/capsules").status_code == 401

    other = make_client()
    login(other, "bob")
    assert other.get("/api/capsules").status_code == 200
    response = world["admin"].post(
        f"/api/admin/friends/{world['ids']['bob']['pid']}/disable",
        headers=world["admin_h"],
    )
    assert response.status_code == 200
    assert other.get("/api/capsules").status_code == 401
    assert make_client().post(
        "/api/auth/login", json={"login_id": "bob", "password": PW}
    ).status_code == 401


def test_8_client_cannot_supply_or_forge_unlock_dates(world):
    admin = world["admin"]
    response = admin.post(
        f"/api/admin/friends/{world['ids']['alice']['pid']}/capsules",
        headers=world["admin_h"],
        json={
            "year": 2150, "content_type": "letter", "body": {"text": "x"},
            "published": True, "unlock_at": "2000-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 422
    client = make_client()
    login(client, "alice")
    future_id = world["ids"]["alice"]["future"]
    assert client.get(
        f"/api/capsules/{future_id}?unlock_at=2000-01-01&now=2300-01-01"
    ).status_code == 404


def test_csrf_required_on_state_changes(world):
    client = make_client()
    login(client, "alice")
    public_id = world["ids"]["alice"]["past"]
    assert client.post(f"/api/capsules/{public_id}/open").status_code == 403
    assert client.post(
        f"/api/capsules/{public_id}/open", headers={"x-csrf-token": "wrong"}
    ).status_code == 403


def test_login_rate_limited(world):
    client = make_client()
    for _ in range(5):
        assert client.post(
            "/api/auth/login", json={"login_id": "alice", "password": "bad" * 5}
        ).status_code == 401
    assert client.post(
        "/api/auth/login", json={"login_id": "alice", "password": PW}
    ).status_code == 429


def test_session_cookie_flags(world):
    client = make_client()
    response = client.post("/api/auth/login", json={"login_id": "alice", "password": PW})
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie


def test_admin_cannot_disable_themselves(world, db):
    admin_user = db.scalar(select(User).where(User.login_id == "admin"))
    response = world["admin"].post(
        f"/api/admin/friends/{admin_user.public_id}/disable",
        headers=world["admin_h"],
    )
    assert response.status_code == 400
    assert admin_user.is_active is True


def test_oversized_letter_and_extra_fields_are_rejected(world):
    admin = world["admin"]
    pid = world["ids"]["alice"]["pid"]
    oversized = admin.post(
        f"/api/admin/friends/{pid}/capsules",
        headers=world["admin_h"],
        json={"year": 2150, "content_type": "letter", "body": {"text": "x" * 20001}},
    )
    extra = admin.post(
        f"/api/admin/friends/{pid}/capsules",
        headers=world["admin_h"],
        json={"year": 2150, "content_type": "letter", "body": {"text": "hi", "html": "<b>hi</b>"}},
    )
    assert oversized.status_code == 422
    assert extra.status_code == 422


def test_oversized_theme_is_rejected(world):
    response = world["admin"].post(
        "/api/admin/friends",
        headers=world["admin_h"],
        json={
            "login_id": "large-theme", "password": PW, "display_name": "Large",
            "birth_month": 1, "birth_day": 1, "theme": {"blob": "x" * 8200},
        },
    )
    assert response.status_code == 422


def test_csrf_dependency_does_not_require_header_for_safe_methods():
    request = Request({"type": "http", "method": "GET", "path": "/api/admin/friends", "headers": []})
    assert csrf_protect(request, SimpleNamespace(csrf_hash="unused")) is None
