"""SQLAlchemy engine, session factory, and FastAPI dependency.

The engine is created lazily so tests can override ``DATABASE_URL`` (e.g.
pointing at SQLite) before the first ``get_db`` call.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.config import get_settings

_engine = None
_session_factory = None


class Base(DeclarativeBase):
    """Declarative base for all application models."""


def _make_engine_url() -> str:
    url = get_settings().database_url
    if url.startswith("sqlite"):
        return url
    # pymysql uses the mysql driver; pool_pre_ping guards against stale pools
    return url


def get_engine():
    global _engine
    if _engine is None:
        url = _make_engine_url()
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(
            url,
            pool_pre_ping=True,
            pool_recycle=1800,
            connect_args=connect_args,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped database session."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """Drop the cached engine/factory (used by tests between cases)."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None
