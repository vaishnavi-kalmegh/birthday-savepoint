"""Shared fixtures. All data is synthetic; no real names, dates, or letters appear in tests."""

from __future__ import annotations

import secrets
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from argon2 import PasswordHasher
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

import app.security as security_module
from app.config import Settings
from app.db import Base, create_db_engine, create_session_factory
from app.main import create_app
from app.models import Capsule, Friend
from app.services import auth as auth_service
from app.services import capsules as capsule_service
from app.services import friends as friend_service

PRODUCTION_HASHER = security_module._hasher  # the real configuration, kept for one test

SECRET = "test-secret-" + "x" * 40
KNOWN_PASSWORD = "synthetic-test-password-1"

# Default "now" for tests: a few days before a March 14 birthday.
T0 = datetime(2027, 3, 10, 12, 0, tzinfo=UTC)


class Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs: float) -> None:
        self.now = self.now + timedelta(**kwargs)


@dataclass
class Account:
    friend: Friend
    password: str


@pytest.fixture(autouse=True)
def fast_password_hashing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Still Argon2id, but with cheap parameters so the suite stays fast.

    test_production_hasher_configuration checks the real configuration separately.
    """
    monkeypatch.setattr(
        security_module, "_hasher", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)
    )


@pytest.fixture
def clock() -> Clock:
    return Clock(T0)


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    eng = create_db_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def make_settings(tmp_path: Path) -> Callable[..., Settings]:
    def _make(**overrides: object) -> Settings:
        values: dict[str, object] = {
            "env": "test",
            "database_url": f"sqlite:///{tmp_path / 'test.db'}",
            "secret_key": SECRET,
            "cookie_secure": True,
            "allowed_origins": ["https://app.example"],
            "login_max_failures_per_account": 5,
            "login_max_failures_per_ip": 50,
        }
        values.update(overrides)
        return Settings(**values)  # type: ignore[arg-type]

    return _make


@pytest.fixture
def app_factory(
    engine: Engine, clock: Clock, make_settings: Callable[..., Settings]
) -> Callable[..., FastAPI]:
    def _make(**overrides: object) -> FastAPI:
        return create_app(settings=make_settings(**overrides), engine=engine, clock=clock)

    return _make


@pytest.fixture
def app(app_factory: Callable[..., FastAPI]) -> FastAPI:
    return app_factory()


@pytest.fixture
def make_client(app: FastAPI) -> Callable[[], TestClient]:
    # https base URL so Secure cookies are sent, as they would be in production.
    return lambda: TestClient(app, base_url="https://testserver")


@pytest.fixture
def client(make_client: Callable[[], TestClient]) -> TestClient:
    return make_client()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    with create_session_factory(engine)() as session:
        yield session


@pytest.fixture
def make_friend(db: Session) -> Callable[..., Account]:
    def _make(
        name: str = "Demo Friend",
        *,
        tz: str = "Asia/Kolkata",
        month: int = 3,
        day: int = 14,
        leap: str = "feb28",
        admin: bool = False,
        ready: bool = True,
    ) -> Account:
        friend, one_time = friend_service.create_friend(
            db,
            display_name=name,
            timezone=tz,
            birth_month=month,
            birth_day=day,
            theme_key="rooftop",
            leap_day_policy=leap,
            is_admin=admin,
        )
        password = one_time
        if ready:
            password = KNOWN_PASSWORD
            auth_service.set_password(db, friend, password, must_change=False)
        return Account(friend=friend, password=password)

    return _make


@pytest.fixture
def make_capsule(db: Session, clock: Clock) -> Callable[..., tuple[Capsule, str]]:
    def _make(
        account: Account, year: int, *, publish: bool = True, marker: str | None = None
    ) -> tuple[Capsule, str]:
        marker = marker or f"MARKER-{secrets.token_hex(6)}"
        capsule = capsule_service.create_capsule(
            db,
            account.friend,
            edition_year=year,
            content_type="letter",
            payload={"title": f"Title {marker}", "paragraphs": [f"Body {marker}"]},
            publish=publish,
            now=clock.now,
        )
        return capsule, marker

    return _make


@pytest.fixture
def login() -> Callable[[TestClient, Account], str]:
    def _login(client: TestClient, account: Account) -> str:
        response = client.post(
            "/api/auth/login",
            json={"entry_slug": account.friend.entry_slug, "password": account.password},
        )
        assert response.status_code == 200, response.text
        token: str = response.json()["csrf_token"]
        return token

    return _login
