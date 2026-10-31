"""Input validation for friends, themes, gifts, and database constraints."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.gifts import validate_gift
from app.models import Capsule
from app.services import friends as friend_service
from app.themes import FALLBACK_THEME_KEY, validate_theme


def _create(db: Session, **overrides):
    args = {
        "display_name": "Demo Friend",
        "timezone": "Asia/Kolkata",
        "birth_month": 3,
        "birth_day": 14,
        "theme_key": "rooftop",
    }
    args.update(overrides)
    return friend_service.create_friend(db, **args)


def test_create_friend_returns_a_one_time_password_that_is_never_stored(db: Session) -> None:
    friend, password = _create(db)
    assert len(password) == 19 and password.count("-") == 3
    assert password not in friend.password_hash
    assert friend.must_change_password is True
    assert friend.public_id and friend.entry_slug and friend.public_id != friend.entry_slug


def test_each_account_gets_distinct_identifiers_and_passwords(db: Session) -> None:
    results = [_create(db, display_name=f"Demo {i}") for i in range(5)]
    assert len({f.public_id for f, _ in results}) == 5
    assert len({f.entry_slug for f, _ in results}) == 5
    assert len({p for _, p in results}) == 5


@pytest.mark.parametrize(
    "overrides",
    [
        {"timezone": "Mars/Olympus_Mons"},
        {"birth_month": 2, "birth_day": 30},
        {"birth_month": 13, "birth_day": 1},
        {"birth_month": 4, "birth_day": 31},
        {"leap_day_policy": "sometime"},
        {"display_name": "   "},
        {"display_name": "x" * 81},
        {"theme_key": "nonexistent"},
        {"theme_key": FALLBACK_THEME_KEY},
        {"theme_config": {"accent": "red"}},
        {"theme_config": {"ambient": "blizzard"}},
        {"theme_config": {"unexpected": "value"}},
    ],
)
def test_invalid_friend_input_is_rejected(db: Session, overrides) -> None:
    with pytest.raises(ValueError):
        _create(db, **overrides)


def test_leap_day_birthday_is_accepted(db: Session) -> None:
    friend, _ = _create(db, birth_month=2, birth_day=29)
    assert (friend.birth_month, friend.birth_day) == (2, 29)


def test_theme_defaults_are_filled_and_overrides_validated() -> None:
    theme = validate_theme("rooftop", {"accent": "#112233"})
    assert theme["accent"] == "#112233"
    assert theme["accent_alt"] and theme["ambient"]
    assert theme["greeting"] is None


def test_letter_payload_validation() -> None:
    ok = validate_gift("letter", {"title": "T", "paragraphs": ["One", "Two"]})
    assert ok["paragraphs"] == ["One", "Two"]
    for bad in (
        {"title": "", "paragraphs": ["x"]},
        {"title": "T", "paragraphs": []},
        {"title": "T", "paragraphs": ["   "]},
        {"title": "T", "paragraphs": ["x" * 6001]},
        {"title": "T", "paragraphs": ["x"], "script": "<script>"},
    ):
        with pytest.raises(ValueError):
            validate_gift("letter", bad)


def test_unknown_gift_type_is_rejected() -> None:
    with pytest.raises(ValueError):
        validate_gift("hologram", {})


def test_database_rejects_a_second_capsule_for_the_same_friend_and_year(
    db: Session, make_friend, make_capsule
) -> None:
    account = make_friend()
    make_capsule(account, 2027)
    with pytest.raises(IntegrityError):
        make_capsule(account, 2027)
    db.rollback()


def test_database_enforces_capsule_state_values(db: Session, make_friend, make_capsule) -> None:
    account = make_friend()
    capsule, _ = make_capsule(account, 2027)
    row = db.get(Capsule, capsule.id)
    row.state = "leaked"
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_deleting_an_account_removes_its_sessions_and_capsules(
    client, db: Session, make_friend, make_capsule, login
) -> None:
    from sqlalchemy import func, select

    from app.models import AuthSession, CapsuleContent

    account = make_friend()
    make_capsule(account, 2026)
    login(client, account)
    db.delete(account.friend)
    db.commit()
    for model in (Capsule, CapsuleContent, AuthSession):
        assert db.execute(select(func.count()).select_from(model)).scalar_one() == 0
