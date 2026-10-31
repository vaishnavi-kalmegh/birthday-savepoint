"""The Alembic migrations must produce exactly the schema the models describe."""

from __future__ import annotations

from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from alembic import command
from app.db import Base

BACKEND = Path(__file__).resolve().parent.parent


def _config(url: str) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_migrations_upgrade_to_a_schema_that_matches_the_models(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    command.upgrade(_config(url), "head")

    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert {"friends", "sessions", "capsules", "capsule_contents", "login_attempts"} <= tables
        with engine.connect() as connection:
            diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
        assert diff == [], f"models and migrations have drifted: {diff}"
    finally:
        engine.dispose()


def test_migrations_downgrade_cleanly(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'roundtrip.db'}"
    cfg = _config(url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    engine = create_engine(url)
    try:
        assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    finally:
        engine.dispose()
