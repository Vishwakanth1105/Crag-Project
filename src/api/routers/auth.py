"""Authentication endpoints: registration, login, logout, session info, CSRF,
and password reset via emailed single-use tokens."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from src.auth.cookies import clear_session_cookie, set_csrf_cookie, set_session_cookie
from src.auth.deps import get_current_user
from src.auth.security import (
    SESSION_COOKIE,
    generate_csrf_token,
    generate_session_token,
    hash_password,
    hash_token,
    session_expiry,
    verify_password,
)
from src.config import get_settings
from src.db.models import PasswordResetToken, User
from src.db.models import Session as DbSession
from src.db.session import get_db
from src.schemas import (
    CsrfResponse,
    DetailResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
)
from src.services.email import password_reset_email, send_email

router = APIRouter(prefix="/auth")

RESET_TOKEN_TTL_MINUTES = 60


def _hash_reset_token(token: str) -> str:
    return hash_token(token)


def _generic_reset_response() -> DetailResponse:
    return DetailResponse(
        message="If that email belongs to an active account, a reset link has been sent."
    )


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def _start_session(db: Session, user: User, response: Response) -> None:
    settings = get_settings()
    token = generate_session_token()
    db.add(
        DbSession(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=session_expiry(),
        )
    )
    db.commit()
    set_session_cookie(response, token, settings.session_ttl_hours * 3600)


@router.get("/csrf", response_model=CsrfResponse)
def get_csrf_token(response: Response) -> CsrfResponse:
    """Establish a double-submit CSRF cookie before any state-changing call."""
    token = generate_csrf_token()
    set_csrf_cookie(response, token)
    return CsrfResponse(csrf_token=token)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest, response: Response, db: Session = Depends(get_db)
) -> UserResponse:
    email = payload.email.lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="user",
    )
    db.add(user)
    db.flush()
    _start_session(db, user, response)
    return _user_response(user)


@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> UserResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None or not verify_password(user.password_hash, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    _start_session(db, user, response)
    return _user_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        db.query(DbSession).filter(DbSession.token_hash == hash_token(token)).delete()
        db.commit()
    clear_session_cookie(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return _user_response(user)


@router.post("/forgot-password", response_model=DetailResponse)
def forgot_password(
    payload: ForgotPasswordRequest, db: Session = Depends(get_db)
) -> DetailResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None or not user.is_active:
        return _generic_reset_response()

    token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_reset_token(token),
            expires_at=datetime.now(UTC) + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
        )
    )
    db.commit()

    settings = get_settings()
    base = settings.frontend_url.rstrip("/")
    link = f"{base}/reset-password?token={token}"
    subject, html = password_reset_email(link)
    send_email(settings, user.email, subject, html)
    return _generic_reset_response()


@router.post("/reset-password", response_model=DetailResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> DetailResponse:
    row = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == _hash_reset_token(payload.token.strip()),
            PasswordResetToken.used_at.is_(None),
        )
        .first()
    )
    now = datetime.now(UTC)
    if row is not None:
        expires_at = row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < now:
            row = None
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired",
        )

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired",
        )

    user.password_hash = hash_password(payload.new_password)
    row.used_at = now
    # Revoke every existing session and void any other outstanding tokens.
    db.query(DbSession).filter(DbSession.user_id == user.id).delete()
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
    db.commit()
    return DetailResponse(message="Password updated. You can now sign in with the new password.")
