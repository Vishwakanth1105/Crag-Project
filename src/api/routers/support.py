"""Support ticket threads: users raise issues, admins answer and resolve."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.auth.deps import get_current_user, require_admin
from src.db.models import SupportMessage, SupportThread, User
from src.db.session import get_db
from src.schemas import (
    CreateSupportThreadRequest,
    DetailResponse,
    SupportMessageOut,
    SupportReplyRequest,
    SupportStatusUpdateRequest,
    SupportThreadListResponse,
    SupportThreadOut,
)

router = APIRouter(prefix="/support")


def _thread_out(thread: SupportThread, *, include_user: bool = False) -> SupportThreadOut:
    user = thread.user if include_user else None
    return SupportThreadOut(
        id=thread.id,
        subject=thread.subject,
        status=thread.status,
        user_email=user.email if user else None,
        user_full_name=user.full_name if user else None,
        messages=[
            SupportMessageOut(
                id=message.id,
                sender_role=message.sender_role,
                content=message.content,
                created_at=message.created_at,
            )
            for message in thread.messages
        ],
        created_at=thread.created_at,
        updated_at=thread.updated_at,
    )


def _get_thread_with_access(
    db: Session, thread_id: int, user: User, *, require_owner_or_admin: bool = True
) -> SupportThread:
    thread = db.get(SupportThread, thread_id)
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    if require_owner_or_admin and thread.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your ticket")
    return thread


@router.post("", response_model=SupportThreadOut, status_code=status.HTTP_201_CREATED)
def create_thread(
    payload: CreateSupportThreadRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SupportThreadOut:
    thread = SupportThread(user_id=user.id, subject=payload.subject, status="open")
    thread.messages.append(
        SupportMessage(sender_id=user.id, sender_role=user.role, content=payload.message)
    )
    db.add(thread)
    db.commit()
    return _thread_out(thread)


@router.get("/mine", response_model=SupportThreadListResponse)
def my_threads(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SupportThreadListResponse:
    threads = (
        db.query(SupportThread)
        .filter(SupportThread.user_id == user.id)
        .order_by(SupportThread.updated_at.desc())
        .all()
    )
    return SupportThreadListResponse(items=[_thread_out(t) for t in threads])


@router.get("/admin/threads", response_model=SupportThreadListResponse)
def all_threads(
    status_filter: str | None = Query(default=None, alias="status"),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SupportThreadListResponse:
    query = db.query(SupportThread)
    if status_filter in {"open", "pending", "resolved"}:
        query = query.filter(SupportThread.status == status_filter)
    threads = query.order_by(SupportThread.updated_at.desc()).all()
    return SupportThreadListResponse(items=[_thread_out(t, include_user=True) for t in threads])


@router.patch("/admin/{thread_id}/status", response_model=DetailResponse)
def update_status(
    thread_id: int,
    payload: SupportStatusUpdateRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DetailResponse:
    thread = db.get(SupportThread, thread_id)
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    thread.status = payload.status
    db.commit()
    return DetailResponse(message=f"Ticket marked {payload.status}")


@router.get("/{thread_id}", response_model=SupportThreadOut)
def get_thread(
    thread_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SupportThreadOut:
    thread = _get_thread_with_access(db, thread_id, user)
    return _thread_out(thread, include_user=user.role == "admin")


@router.post("/{thread_id}/messages", response_model=DetailResponse)
def reply_to_thread(
    thread_id: int,
    payload: SupportReplyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DetailResponse:
    thread = _get_thread_with_access(db, thread_id, user)
    is_admin_sender = user.role == "admin"
    thread.messages.append(
        SupportMessage(
            sender_id=user.id,
            sender_role="admin" if is_admin_sender else "user",
            content=payload.content,
        )
    )
    if is_admin_sender and thread.status == "open":
        thread.status = "pending"
    elif not is_admin_sender and thread.status == "resolved":
        # Reopening a resolved ticket puts it back in the admin queue.
        thread.status = "open"
    db.commit()
    return DetailResponse(message="Reply sent")
