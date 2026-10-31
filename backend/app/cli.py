"""Provisioning commands. Run from the backend directory:

    python -m app.cli create-friend --name "..." --timezone Asia/Kolkata \
        --birthday 03-14 --theme rooftop
    python -m app.cli add-letter --friend <public_id> --year 2027 \
        --file private/letter.json --publish
    python -m app.cli reset-password --friend <public_id>
    python -m app.cli revoke-sessions --friend <public_id>
    python -m app.cli seed-demo        (development only, synthetic data)

One-time passwords are printed once to the terminal and are never stored or logged.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import create_db_engine, create_session_factory
from app.services import auth as auth_service
from app.services import capsules as capsule_service
from app.services import friends as friend_service


def _now() -> datetime:
    return datetime.now(UTC)


def _parse_birthday(value: str) -> tuple[int, int]:
    try:
        month_s, day_s = value.split("-")
        return int(month_s), int(day_s)
    except ValueError as exc:
        raise SystemExit("--birthday must look like MM-DD, for example 03-14") from exc


def _require_friend(db: Session, public_id: str):  # type: ignore[no-untyped-def]
    friend = friend_service.get_by_public_id(db, public_id)
    if friend is None:
        raise SystemExit("No account with that id.")
    return friend


def _print_credentials(settings: Settings, entry_slug: str, password: str) -> None:
    link = f"{settings.public_base_url.rstrip('/')}/w/{entry_slug}"
    print(f"Entry link:        {link}")
    print(f"One-time password: {password}")
    print("Send these separately and privately. The password is shown only once.")


def cmd_create_friend(db: Session, settings: Settings, args: argparse.Namespace) -> None:
    month, day = _parse_birthday(args.birthday)
    config = {
        k: v
        for k, v in {
            "accent": args.accent,
            "accent_alt": args.accent_alt,
            "ambient": args.ambient,
            "greeting": args.greeting,
        }.items()
        if v is not None
    }
    try:
        friend, password = friend_service.create_friend(
            db,
            display_name=args.name,
            timezone=args.timezone,
            birth_month=month,
            birth_day=day,
            theme_key=args.theme,
            theme_config=config,
            leap_day_policy=args.leap_policy,
            is_admin=args.admin,
        )
    except ValueError as exc:
        raise SystemExit(f"Could not create account: {exc}") from exc
    print(f"Account id: {friend.public_id}")
    _print_credentials(settings, friend.entry_slug, password)


def cmd_add_letter(db: Session, settings: Settings, args: argparse.Namespace) -> None:
    friend = _require_friend(db, args.friend)
    try:
        payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
        capsule = capsule_service.create_capsule(
            db,
            friend,
            edition_year=args.year,
            content_type="letter",
            payload=payload,
            publish=args.publish,
            now=_now(),
        )
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Could not add letter: {exc}") from exc
    state = "published" if args.publish else "draft"
    print(
        f"Capsule {capsule.public_id} ({capsule.edition_year}, {state}), "
        f"unlocks {capsule.unlock_at.isoformat()}"
    )


def cmd_reset_password(db: Session, settings: Settings, args: argparse.Namespace) -> None:
    friend = _require_friend(db, args.friend)
    password = friend_service.reset_password(db, friend, now=_now())
    print("All sessions for this account were revoked.")
    _print_credentials(settings, friend.entry_slug, password)


def cmd_revoke_sessions(db: Session, settings: Settings, args: argparse.Namespace) -> None:
    friend = _require_friend(db, args.friend)
    auth_service.revoke_all_sessions(db, friend.id, now=_now())
    print("All sessions for this account were revoked.")


def cmd_seed_demo(db: Session, settings: Settings, args: argparse.Namespace) -> None:
    if settings.env != "development":
        raise SystemExit("seed-demo only runs with SAVEPOINT_ENV=development.")
    now = _now()
    friend, password = friend_service.create_friend(
        db,
        display_name="Demo Friend",
        timezone="Asia/Kolkata",
        birth_month=now.month,
        birth_day=now.day,
        theme_key="rooftop",
    )
    capsule_service.create_capsule(
        db,
        friend,
        edition_year=now.year,
        content_type="letter",
        payload={
            "title": "A demo letter",
            "greeting": "Hello, Demo Friend.",
            "paragraphs": [
                "This is synthetic text used to check the reading experience.",
                "Replace it with a real letter using the add-letter command.",
            ],
            "signoff": "From the archive",
        },
        publish=True,
        now=now,
    )
    print("Created a synthetic demo account with one published letter for today's date.")
    print(f"Account id: {friend.public_id}")
    _print_credentials(settings, friend.entry_slug, password)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="app.cli", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create-friend", help="create an account")
    p.add_argument("--name", required=True)
    p.add_argument("--timezone", required=True, help="IANA name, e.g. Asia/Kolkata")
    p.add_argument("--birthday", required=True, help="MM-DD")
    p.add_argument("--theme", required=True)
    p.add_argument("--leap-policy", default="feb28", choices=["feb28", "mar1"])
    p.add_argument("--accent")
    p.add_argument("--accent-alt")
    p.add_argument("--ambient")
    p.add_argument("--greeting")
    p.add_argument("--admin", action="store_true")
    p.set_defaults(func=cmd_create_friend)

    p = sub.add_parser("add-letter", help="add a letter capsule from a JSON file")
    p.add_argument("--friend", required=True, help="account id")
    p.add_argument("--year", required=True, type=int)
    p.add_argument("--file", required=True)
    p.add_argument("--publish", action="store_true")
    p.set_defaults(func=cmd_add_letter)

    p = sub.add_parser("reset-password", help="issue a new one-time password")
    p.add_argument("--friend", required=True)
    p.set_defaults(func=cmd_reset_password)

    p = sub.add_parser("revoke-sessions", help="sign an account out everywhere")
    p.add_argument("--friend", required=True)
    p.set_defaults(func=cmd_revoke_sessions)

    p = sub.add_parser("seed-demo", help="development only: create a synthetic demo account")
    p.set_defaults(func=cmd_seed_demo)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    with create_session_factory(engine)() as db:
        args.func(db, settings, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
