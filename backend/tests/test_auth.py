"""Authentication, sessions, CSRF, origin checks, and brute-force protection."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuthSession, Friend
from app.services import auth as auth_service
from app.services import friends as friend_service
from tests.conftest import KNOWN_PASSWORD, Account, Clock

COOKIE = "sp_session"


def test_login_sets_a_hardened_session_cookie(client, make_friend) -> None:
    account = make_friend()
    response = client.post(
        "/api/auth/login",
        json={"entry_slug": account.friend.entry_slug, "password": account.password},
    )
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert f"{COOKIE}=" in cookie
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=lax" in cookie
    assert "path=/" in cookie
    assert "max-age=" in cookie
    assert "csrf_token" in response.json()


def test_passwords_and_session_tokens_are_not_stored_in_plaintext(
    client, make_friend, login, db: Session
) -> None:
    account = make_friend()
    login(client, account)
    raw_token = client.cookies.get(COOKIE)
    assert raw_token

    stored_hash = db.execute(select(Friend.password_hash)).scalars().one()
    assert stored_hash.startswith("$argon2id$")
    assert KNOWN_PASSWORD not in stored_hash

    token_hashes = list(db.execute(select(AuthSession.token_hash)).scalars())
    assert token_hashes and raw_token not in token_hashes
    assert all(len(h) == 64 for h in token_hashes)


def test_wrong_password_and_unknown_account_are_indistinguishable(client, make_friend) -> None:
    account = make_friend()
    wrong_password = client.post(
        "/api/auth/login", json={"entry_slug": account.friend.entry_slug, "password": "nope-nope"}
    )
    unknown_account = client.post(
        "/api/auth/login", json={"entry_slug": "x" * 22, "password": "nope-nope"}
    )
    assert wrong_password.status_code == unknown_account.status_code == 401
    assert wrong_password.json() == unknown_account.json()
    assert COOKIE not in wrong_password.headers.get("set-cookie", "")


def test_deactivated_account_cannot_log_in_or_keep_a_session(
    client, make_friend, login, db: Session
) -> None:
    account = make_friend()
    login(client, account)
    assert client.get("/api/me").status_code == 200

    account.friend.is_active = False
    db.commit()

    assert client.get("/api/me").status_code == 401
    again = client.post(
        "/api/auth/login",
        json={"entry_slug": account.friend.entry_slug, "password": account.password},
    )
    assert again.status_code == 401


def test_logout_revokes_the_session_server_side(client, make_client, make_friend, login) -> None:
    account = make_friend()
    csrf = login(client, account)
    token = client.cookies.get(COOKIE)
    assert token

    assert client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204

    # Replaying the old cookie from a fresh client must fail: revocation is server-side,
    # not just a cleared cookie.
    replay = make_client()
    replay.cookies.set(COOKIE, token, domain="testserver")
    assert replay.get("/api/me").status_code == 401


def test_session_expires_after_its_ttl(client, make_friend, login, clock: Clock) -> None:
    account = make_friend()
    login(client, account)
    clock.advance(days=13, hours=23)
    assert client.get("/api/me").status_code == 200
    clock.advance(hours=2)
    assert client.get("/api/me").status_code == 401


def test_admin_sessions_have_a_shorter_ttl(make_client, make_friend, login, clock: Clock) -> None:
    admin = make_friend("Demo Admin", admin=True)
    friend = make_friend("Demo Friend")
    admin_client, friend_client = make_client(), make_client()
    login(admin_client, admin)
    login(friend_client, friend)
    clock.advance(hours=9)
    assert admin_client.get("/api/me").status_code == 401
    assert friend_client.get("/api/me").status_code == 200


def test_revoking_all_sessions_ends_existing_sessions(
    client, make_friend, login, db: Session, clock: Clock
) -> None:
    account = make_friend()
    login(client, account)
    assert client.get("/api/me").status_code == 200
    auth_service.revoke_all_sessions(db, account.friend.id, now=clock.now)
    assert client.get("/api/me").status_code == 401


def test_password_reset_revokes_sessions_and_forces_a_change(
    client, make_friend, login, db: Session, clock: Clock
) -> None:
    account = make_friend()
    login(client, account)
    new_one_time = friend_service.reset_password(db, account.friend, now=clock.now)

    assert client.get("/api/me").status_code == 401
    old = client.post(
        "/api/auth/login",
        json={"entry_slug": account.friend.entry_slug, "password": account.password},
    )
    assert old.status_code == 401
    fresh = client.post(
        "/api/auth/login",
        json={"entry_slug": account.friend.entry_slug, "password": new_one_time},
    )
    assert fresh.status_code == 200
    assert fresh.json()["must_change_password"] is True


def test_change_password_flow(client, make_client, make_friend, login) -> None:
    account = make_friend()
    other_device = make_client()
    login(other_device, account)
    csrf = login(client, account)

    wrong = client.post(
        "/api/auth/change-password",
        json={"current_password": "not-my-password", "new_password": "a-brand-new-password-2"},
        headers={"X-CSRF-Token": csrf},
    )
    assert wrong.status_code == 401

    same = client.post(
        "/api/auth/change-password",
        json={"current_password": KNOWN_PASSWORD, "new_password": KNOWN_PASSWORD},
        headers={"X-CSRF-Token": csrf},
    )
    assert same.status_code == 422

    ok = client.post(
        "/api/auth/change-password",
        json={"current_password": KNOWN_PASSWORD, "new_password": "a-brand-new-password-2"},
        headers={"X-CSRF-Token": csrf},
    )
    assert ok.status_code == 204
    assert client.get("/api/me").status_code == 200  # the acting session survives
    assert other_device.get("/api/me").status_code == 401  # every other session is revoked

    assert (
        client.post(
            "/api/auth/login",
            json={"entry_slug": account.friend.entry_slug, "password": KNOWN_PASSWORD},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"entry_slug": account.friend.entry_slug, "password": "a-brand-new-password-2"},
        ).status_code
        == 200
    )


def test_short_new_password_is_rejected(client, make_friend, login) -> None:
    account = make_friend()
    csrf = login(client, account)
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": KNOWN_PASSWORD, "new_password": "short"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 422


def test_repeated_failures_lock_the_account_out_even_for_the_right_password(
    client, make_friend, clock: Clock
) -> None:
    account = make_friend()
    slug = account.friend.entry_slug
    for _ in range(5):
        r = client.post("/api/auth/login", json={"entry_slug": slug, "password": "wrong-guess"})
        assert r.status_code == 401

    blocked = client.post(
        "/api/auth/login", json={"entry_slug": slug, "password": account.password}
    )
    assert blocked.status_code == 429
    assert "retry-after" in blocked.headers

    clock.advance(minutes=16)
    recovered = client.post(
        "/api/auth/login", json={"entry_slug": slug, "password": account.password}
    )
    assert recovered.status_code == 200


def test_failures_against_one_account_do_not_lock_another(client, make_friend) -> None:
    a, b = make_friend("Demo A"), make_friend("Demo B")
    for _ in range(6):
        client.post(
            "/api/auth/login", json={"entry_slug": a.friend.entry_slug, "password": "x" * 10}
        )
    ok = client.post(
        "/api/auth/login", json={"entry_slug": b.friend.entry_slug, "password": b.password}
    )
    assert ok.status_code == 200


def test_ip_throttle_blocks_guessing_across_many_slugs(
    app_factory: Callable[..., FastAPI], make_friend
) -> None:
    account = make_friend()
    strict = TestClient(app_factory(login_max_failures_per_ip=3), base_url="https://testserver")
    for i in range(3):
        strict.post(
            "/api/auth/login", json={"entry_slug": f"unknown-slug-{i:04d}", "password": "x" * 10}
        )
    blocked = strict.post(
        "/api/auth/login",
        json={"entry_slug": account.friend.entry_slug, "password": account.password},
    )
    assert blocked.status_code == 429


def test_failed_attempt_keys_are_hashed(client, make_friend, db: Session) -> None:
    account = make_friend()
    client.post(
        "/api/auth/login", json={"entry_slug": account.friend.entry_slug, "password": "x" * 10}
    )
    from app.models import LoginAttempt

    keys = list(db.execute(select(LoginAttempt.key_hash)).scalars())
    assert keys
    assert all(account.friend.entry_slug not in k and len(k) == 64 for k in keys)


def test_unsafe_requests_require_the_csrf_token(client, make_client, make_friend, login) -> None:
    a, b = make_friend("Demo A"), make_friend("Demo B")
    csrf_a = login(client, a)
    other = make_client()
    csrf_b = login(other, b)

    assert client.post("/api/auth/logout").status_code == 403  # missing
    assert client.post("/api/auth/logout", headers={"X-CSRF-Token": "nope"}).status_code == 403
    # A valid token belonging to a different session is not accepted either.
    assert client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_b}).status_code == 403
    assert client.get("/api/me").status_code == 200  # still signed in after the rejected attempts
    assert client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_a}).status_code == 204


def test_cross_site_origin_is_rejected_on_unsafe_requests(client, make_friend) -> None:
    account = make_friend()
    body = {"entry_slug": account.friend.entry_slug, "password": account.password}

    evil = client.post("/api/auth/login", json=body, headers={"Origin": "https://evil.example"})
    assert evil.status_code == 403
    assert COOKIE not in evil.headers.get("set-cookie", "")

    configured = client.post(
        "/api/auth/login", json=body, headers={"Origin": "https://app.example"}
    )
    assert configured.status_code == 200


def test_same_origin_requests_are_accepted(client, make_friend) -> None:
    account = make_friend()
    response = client.post(
        "/api/auth/login",
        json={"entry_slug": account.friend.entry_slug, "password": account.password},
        headers={"Origin": "https://testserver"},
    )
    assert response.status_code == 200


def test_request_bodies_reject_unknown_fields_and_oversized_passwords(client, make_friend) -> None:
    account = make_friend()
    extra = client.post(
        "/api/auth/login",
        json={"entry_slug": account.friend.entry_slug, "password": account.password, "admin": True},
    )
    assert extra.status_code == 422
    huge = client.post(
        "/api/auth/login",
        json={"entry_slug": account.friend.entry_slug, "password": "a" * 10_000},
    )
    assert huge.status_code == 422


@pytest.mark.parametrize("path", ["/api/health", "/api/entry/whatever-slug-value"])
def test_api_responses_carry_security_headers_and_are_not_cacheable(client, path: str) -> None:
    response = client.get(path)
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_api_docs_are_not_exposed_outside_development(client) -> None:
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_settings_reject_weak_or_placeholder_secrets(make_settings) -> None:
    with pytest.raises(ValueError):
        make_settings(secret_key="short")
    with pytest.raises(ValueError):
        make_settings(secret_key="change-me-" + "x" * 40)


def test_production_hasher_configuration() -> None:
    from tests.conftest import PRODUCTION_HASHER

    digest = PRODUCTION_HASHER.hash("synthetic-check")
    assert digest.startswith("$argon2id$")
    assert not PRODUCTION_HASHER.check_needs_rehash(digest)
    # The library defaults are far stronger than the cheap test parameters.
    assert PRODUCTION_HASHER._parameters.memory_cost >= 19_456  # type: ignore[attr-defined]
    assert PRODUCTION_HASHER._parameters.time_cost >= 2  # type: ignore[attr-defined]


def test_helper_account_type_is_exercised(make_friend) -> None:
    assert isinstance(make_friend(), Account)
