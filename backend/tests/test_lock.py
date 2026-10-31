"""Server-side capsule locking. Future content must never reach the client before unlock.

Fixture timeline (see conftest): the friend's birthday is March 14 in Asia/Kolkata, so the 2027
capsule unlocks at 2027-03-13 18:30 UTC. "Now" starts at 2027-03-10 12:00 UTC.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Capsule
from app.services import capsules as capsule_service
from tests.conftest import Clock

UNLOCK_2027 = datetime(2027, 3, 13, 18, 30, tzinfo=UTC)


def _opened_at(db: Session, capsule: Capsule):
    fresh = db.get(Capsule, capsule.id)
    db.refresh(fresh)
    return fresh.opened_at


def test_locked_capsule_appears_only_as_a_sealed_slot(
    client, make_friend, make_capsule, login
) -> None:
    account = make_friend()
    capsule, marker = make_capsule(account, 2027)  # published, but not unlocked yet
    login(client, account)

    response = client.get("/api/capsules")
    body = response.json()

    assert body["capsules"] == []
    assert set(body["next_sealed"]) == {"edition_year", "unlock_at"}
    assert body["next_sealed"]["edition_year"] == 2027
    assert body["next_sealed"]["unlock_at"].startswith("2027-03-13T18:30:00")
    # Nothing about the gift, even its existence, type, or identifier, is in the response.
    assert marker not in response.text
    assert capsule.public_id not in response.text
    assert "letter" not in response.text.lower()
    assert "gift" not in response.text.lower()


def test_sealed_slot_is_identical_whether_or_not_a_gift_was_prepared(
    make_client, make_friend, make_capsule, login
) -> None:
    prepared, empty = make_friend("Demo Prepared"), make_friend("Demo Empty")
    make_capsule(prepared, 2027)
    c1, c2 = make_client(), make_client()
    login(c1, prepared)
    login(c2, empty)

    one = c1.get("/api/capsules").json()
    two = c2.get("/api/capsules").json()
    assert one["next_sealed"] == two["next_sealed"]
    assert one["capsules"] == two["capsules"] == []


def test_locked_capsule_cannot_be_fetched_by_its_real_identifier(
    client, make_friend, make_capsule, login
) -> None:
    account = make_friend()
    capsule, marker = make_capsule(account, 2027)
    csrf = login(client, account)

    real = client.get(f"/api/capsules/{capsule.public_id}")
    guess = client.get("/api/capsules/aaaaaaaaaaaaaaaa")
    assert real.status_code == 404
    assert real.json() == guess.json()  # identical to a capsule that does not exist
    assert marker not in real.text

    opened = client.post(f"/api/capsules/{capsule.public_id}/open", headers={"X-CSRF-Token": csrf})
    assert opened.status_code == 404
    assert marker not in opened.text


def test_opening_a_locked_capsule_does_not_change_its_state(
    client, make_friend, make_capsule, login, db: Session
) -> None:
    account = make_friend()
    capsule, _ = make_capsule(account, 2027)
    csrf = login(client, account)
    client.post(f"/api/capsules/{capsule.public_id}/open", headers={"X-CSRF-Token": csrf})
    assert _opened_at(db, capsule) is None


def test_unlock_boundary_is_exact(client, make_friend, make_capsule, login, clock: Clock) -> None:
    account = make_friend()
    capsule, marker = make_capsule(account, 2027)
    login(client, account)

    clock.now = UNLOCK_2027 - timedelta(seconds=1)
    assert client.get(f"/api/capsules/{capsule.public_id}").status_code == 404
    assert client.get("/api/capsules").json()["capsules"] == []

    clock.now = UNLOCK_2027
    unlocked = client.get(f"/api/capsules/{capsule.public_id}")
    assert unlocked.status_code == 200
    assert marker in unlocked.text
    assert [c["id"] for c in client.get("/api/capsules").json()["capsules"]] == [capsule.public_id]

    # Once unlocked, the sealed slot moves on to next year.
    assert client.get("/api/capsules").json()["next_sealed"]["edition_year"] == 2028


def test_unpublished_capsules_stay_invisible_even_after_their_unlock_date(
    client, make_friend, make_capsule, login, clock: Clock
) -> None:
    account = make_friend()
    capsule, marker = make_capsule(account, 2027, publish=False)

    clock.now = UNLOCK_2027 + timedelta(days=30)
    csrf = login(client, account)  # log in after moving the clock so the session is still valid
    archive = client.get("/api/capsules")
    assert archive.json()["capsules"] == []
    assert marker not in archive.text
    assert client.get(f"/api/capsules/{capsule.public_id}").status_code == 404
    assert (
        client.post(
            f"/api/capsules/{capsule.public_id}/open", headers={"X-CSRF-Token": csrf}
        ).status_code
        == 404
    )


def test_future_editions_stay_hidden_when_the_current_one_is_unlocked(
    client, make_friend, make_capsule, login, clock: Clock
) -> None:
    account = make_friend()
    this_year, _ = make_capsule(account, 2027)
    next_year, next_marker = make_capsule(account, 2028)
    far_future, far_marker = make_capsule(account, 2035)
    login(client, account)

    clock.now = UNLOCK_2027 + timedelta(hours=1)
    response = client.get("/api/capsules")
    assert [c["id"] for c in response.json()["capsules"]] == [this_year.public_id]
    for hidden in (next_year, far_future):
        assert hidden.public_id not in response.text
        assert client.get(f"/api/capsules/{hidden.public_id}").status_code == 404
    assert next_marker not in response.text and far_marker not in response.text


def test_client_supplied_time_and_unlock_values_are_ignored(
    client, make_friend, make_capsule, login
) -> None:
    account = make_friend()
    capsule, marker = make_capsule(account, 2027)
    csrf = login(client, account)
    spoofed_headers = {
        "X-CSRF-Token": csrf,
        "Date": "Mon, 01 Jan 2035 00:00:00 GMT",
        "X-Client-Time": "2035-01-01T00:00:00Z",
        "X-Forwarded-For": "203.0.113.9",
        "If-Modified-Since": "Mon, 01 Jan 2035 00:00:00 GMT",
    }
    spoofed_params = {"now": "2035-01-01T00:00:00Z", "unlock_at": "2000-01-01", "force": "true"}

    for response in (
        client.get(
            f"/api/capsules/{capsule.public_id}", params=spoofed_params, headers=spoofed_headers
        ),
        client.post(
            f"/api/capsules/{capsule.public_id}/open",
            params=spoofed_params,
            headers=spoofed_headers,
            json={"unlock_at": "2000-01-01T00:00:00Z", "now": "2035-01-01T00:00:00Z"},
        ),
        client.get("/api/capsules", params=spoofed_params, headers=spoofed_headers),
    ):
        assert marker not in response.text
    assert (
        client.get(f"/api/capsules/{capsule.public_id}", params=spoofed_params).status_code == 404
    )


def test_no_code_path_accepts_an_unlock_date_from_outside() -> None:
    # The unlock moment is derived from the friend's birthday, timezone, and leap-day policy.
    params = inspect.signature(capsule_service.create_capsule).parameters
    assert "unlock_at" not in params and "unlock_date" not in params


def test_tampered_stored_unlock_date_in_the_future_still_blocks_access(
    client, make_friend, make_capsule, login, db: Session, clock: Clock
) -> None:
    # Authorization compares the stored unlock moment with server time on every request.
    account = make_friend()
    capsule, marker = make_capsule(account, 2026)
    login(client, account)
    assert client.get(f"/api/capsules/{capsule.public_id}").status_code == 200

    row = db.get(Capsule, capsule.id)
    row.unlock_at = clock.now + timedelta(days=1)
    db.commit()
    blocked = client.get(f"/api/capsules/{capsule.public_id}")
    assert blocked.status_code == 404
    assert marker not in blocked.text


def test_opening_persists_across_requests_sessions_and_time(
    client, make_client, make_friend, make_capsule, login, clock: Clock
) -> None:
    account = make_friend()
    capsule, marker = make_capsule(account, 2026)
    csrf = login(client, account)

    archive = client.get("/api/capsules").json()
    assert archive["capsules"][0]["opened_at"] is None

    first = client.post(f"/api/capsules/{capsule.public_id}/open", headers={"X-CSRF-Token": csrf})
    assert first.status_code == 200
    opened_at = first.json()["opened_at"]
    assert opened_at is not None
    assert marker in first.text

    clock.advance(days=3)
    again = client.post(f"/api/capsules/{capsule.public_id}/open", headers={"X-CSRF-Token": csrf})
    assert again.json()["opened_at"] == opened_at  # idempotent: the first opening time is kept

    fresh_session = make_client()
    login(fresh_session, account)
    assert fresh_session.get("/api/capsules").json()["capsules"][0]["opened_at"] == opened_at


def test_previous_capsules_remain_available_to_their_owner(
    client, make_friend, make_capsule, login, clock: Clock
) -> None:
    account = make_friend()
    old, old_marker = make_capsule(account, 2025)
    recent, recent_marker = make_capsule(account, 2026)

    clock.now = datetime(2029, 6, 1, tzinfo=UTC)
    login(client, account)
    years = [c["edition_year"] for c in client.get("/api/capsules").json()["capsules"]]
    assert years == [2026, 2025]  # newest first
    assert old_marker in client.get(f"/api/capsules/{old.public_id}").text
    assert recent_marker in client.get(f"/api/capsules/{recent.public_id}").text


def test_gift_endpoints_are_blocked_until_the_one_time_password_is_changed(
    client, make_friend, make_capsule, login, clock: Clock
) -> None:
    account = make_friend(ready=False)
    capsule, marker = make_capsule(account, 2026)
    csrf = login(client, account)

    me = client.get("/api/me")
    assert me.status_code == 200 and me.json()["must_change_password"] is True

    for response in (
        client.get("/api/capsules"),
        client.get(f"/api/capsules/{capsule.public_id}"),
        client.post(f"/api/capsules/{capsule.public_id}/open", headers={"X-CSRF-Token": csrf}),
    ):
        assert response.status_code == 403
        assert response.json() == {"detail": "password_change_required"}
        assert marker not in response.text

    changed = client.post(
        "/api/auth/change-password",
        json={"current_password": account.password, "new_password": "a-brand-new-password-2"},
        headers={"X-CSRF-Token": csrf},
    )
    assert changed.status_code == 204
    assert client.get("/api/capsules").status_code == 200


def test_leap_day_friend_unlocks_by_their_stored_policy(
    make_client, make_friend, make_capsule, login, clock: Clock
) -> None:
    feb28 = make_friend("Demo Feb28", tz="UTC", month=2, day=29, leap="feb28")
    mar1 = make_friend("Demo Mar1", tz="UTC", month=2, day=29, leap="mar1")
    c_feb28, _ = make_capsule(feb28, 2027)
    c_mar1, _ = make_capsule(mar1, 2027)
    a, b = make_client(), make_client()
    login(a, feb28)
    login(b, mar1)

    clock.now = datetime(2027, 2, 28, 12, 0, tzinfo=UTC)
    assert a.get(f"/api/capsules/{c_feb28.public_id}").status_code == 200
    assert b.get(f"/api/capsules/{c_mar1.public_id}").status_code == 404

    clock.now = datetime(2027, 3, 1, 0, 0, tzinfo=UTC)
    assert b.get(f"/api/capsules/{c_mar1.public_id}").status_code == 200
