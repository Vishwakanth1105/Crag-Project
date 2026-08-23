"""Command-line administration utilities.

Usage:
    python -m src.cli create-admin --email admin@example.com --password s3cret
"""

from __future__ import annotations

import argparse

from src.auth.security import hash_password
from src.db.models import User
from src.db.session import get_session_factory


def create_admin(email: str, password: str, full_name: str = "Administrator") -> None:
    email = email.lower().strip()
    session = get_session_factory()()
    try:
        user = session.query(User).filter(User.email == email).first()
        if user is not None:
            user.password_hash = hash_password(password)
            user.role = "admin"
            user.is_active = True
            session.commit()
            print(f"updated {email} to admin")
        else:
            session.add(
                User(
                    email=email,
                    password_hash=hash_password(password),
                    full_name=full_name,
                    role="admin",
                )
            )
            session.commit()
            print(f"created admin {email}")
    finally:
        session.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="src.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    admin = subparsers.add_parser("create-admin", help="Create or promote an admin user")
    admin.add_argument("--email", required=True)
    admin.add_argument("--password", required=True)
    admin.add_argument("--full-name", default="Administrator")

    args = parser.parse_args(argv)
    if args.command == "create-admin":
        create_admin(args.email, args.password, args.full_name)
    else:  # pragma: no cover - argparse rejects unknown subcommands
        parser.error(f"unknown command {args.command}")


if __name__ == "__main__":
    main()
