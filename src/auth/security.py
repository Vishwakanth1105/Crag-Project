"""Password hashing (argon2id), opaque session tokens, and CSRF helpers."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from src.config import get_settings

SESSION_COOKIE = "rag_session"
CSRF_COOKIE = "rag_csrf"

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def hash_token(token: str) -> str:
    """Deterministic digest used to store tokens at rest (never the raw token)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def session_expiry(ttl_hours: int | None = None) -> datetime:
    ttl = ttl_hours if ttl_hours is not None else get_settings().session_ttl_hours
    return datetime.now(UTC) + timedelta(hours=ttl)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
