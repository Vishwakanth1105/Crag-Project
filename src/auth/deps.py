"""FastAPI dependencies for authentication, CSRF, and authorization."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.auth.security import CSRF_COOKIE, SESSION_COOKIE, hash_token
from src.db.models import Session as DbSession
from src.db.models import User
from src.db.session import get_db


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise _unauthorized()

    record = db.query(DbSession).filter(DbSession.token_hash == hash_token(token)).first()
    if record is None:
        raise _unauthorized()

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        db.delete(record)
        db.commit()
        raise _unauthorized("Session expired")

    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise _unauthorized()

    record.last_used_at = datetime.now(UTC)
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return user


def validate_csrf(request: Request) -> None:
    """Double-submit CSRF: require the header to echo the cookie value.

    Safe methods are exempt; the frontend fetches a fresh token from
    ``GET /api/v1/auth/csrf`` on startup and echoes it as ``X-CSRF-Token``.
    """
    if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
        return
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get("X-CSRF-Token")
    if not cookie or not header or not secrets.compare_digest(cookie, header):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing or invalid",
        )
