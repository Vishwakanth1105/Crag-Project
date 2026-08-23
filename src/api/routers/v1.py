"""Aggregate v1 API router with CSRF protection for all state-changing calls."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.routers import admin, auth, conversations, documents, info
from src.auth.deps import validate_csrf

router = APIRouter(dependencies=[Depends(validate_csrf)])
router.include_router(auth.router)
router.include_router(info.router)
router.include_router(documents.router)
router.include_router(conversations.router)
router.include_router(admin.router)
