"""Authentication endpoints: registration, login, logout, session info, CSRF."""

from __future__ import annotations

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
from src.db.models import Session as DbSession
from src.db.models import User
from src.db.session import get_db
from src.schemas import CsrfResponse, LoginRequest, RegisterRequest, UserResponse

router = APIRouter(prefix="/auth")


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
