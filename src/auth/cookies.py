"""Cookie helpers for the DB-backed session and double-submit CSRF tokens."""

from __future__ import annotations

from fastapi import Response

from src.auth.security import CSRF_COOKIE, SESSION_COOKIE
from src.config import Settings, get_settings


def _secure(settings: Settings) -> bool:
    return settings.cookie_secure


def set_session_cookie(response: Response, token: str, max_age_seconds: int) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=_secure(settings),
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        SESSION_COOKIE,
        httponly=True,
        samesite="lax",
        secure=_secure(settings),
        path="/",
    )


def set_csrf_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        CSRF_COOKIE,
        token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=False,
        samesite="lax",
        secure=_secure(settings),
        path="/",
    )
