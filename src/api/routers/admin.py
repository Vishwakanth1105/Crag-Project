"""Administrative endpoints (require the admin role)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.auth.deps import require_admin
from src.config import get_settings
from src.db.models import (
    Conversation,
    Document,
    IngestionJob,
    Message,
    PasswordResetToken,
    QueryLog,
    SupportMessage,
    SupportThread,
    User,
)
from src.db.models import (
    Session as DbSession,
)
from src.db.session import get_db
from src.ingestion import neo4j_indexer, qdrant_indexer
from src.schemas import (
    AdminConversationItem,
    AdminConversationsResponse,
    AdminDocumentResponse,
    AdminDocumentsResponse,
    AdminIngestionsResponse,
    AdminMessageItem,
    AdminMessagesResponse,
    AdminQueryLogItem,
    AdminQueryLogsResponse,
    AdminUserDetailResponse,
    AdminUserResponse,
    AdminUsersResponse,
    AdminUserStatusUpdateRequest,
    DependencyStatus,
    DocumentResponse,
    IngestionJobResponse,
    RecentConversationItem,
    SystemStats,
)
from src.storage.minio_client import StorageClient

router = APIRouter(prefix="/admin")


def _admin_user_response(user: User) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def _document_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        file_name=document.file_name,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        status=document.status,
        error=document.error,
        created_at=document.created_at,
    )


def _job_response(job: IngestionJob) -> IngestionJobResponse:
    return IngestionJobResponse(
        id=job.id,
        document_id=job.document_id,
        status=job.status,
        parent_chunks=job.parent_chunks,
        child_chunks=job.child_chunks,
        graph_relationships=job.graph_relationships,
        error=job.error,
        created_at=job.created_at,
    )


def _dependency_status(name: str, ready: bool, detail: str | None) -> DependencyStatus:
    return DependencyStatus(
        name=name,
        status="ready" if ready else "unavailable",
        detail=detail,
    )


@router.get("/users", response_model=AdminUsersResponse)
def admin_users(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUsersResponse:
    users = db.query(User).order_by(User.created_at.desc()).all()
    return AdminUsersResponse(items=[_admin_user_response(user) for user in users])


def _get_managed_user(db: Session, user_id: int, acting_admin: User) -> User:
    """Load a user an admin may act on: not themselves, not another admin."""
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == acting_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Admins cannot act on themselves"
        )
    if target.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Other admins cannot be modified"
        )
    return target


@router.get("/users/{user_id}", response_model=AdminUserDetailResponse)
def admin_user_detail(
    user_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserDetailResponse:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    recent_documents = (
        db.query(Document)
        .filter(Document.user_id == target.id)
        .order_by(Document.created_at.desc())
        .limit(5)
        .all()
    )
    conversation_rows = (
        db.query(Conversation, func.count(Message.id))
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id == target.id)
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc())
        .limit(5)
        .all()
    )

    return AdminUserDetailResponse(
        profile=_admin_user_response(target),
        document_count=db.query(Document).filter(Document.user_id == target.id).count(),
        conversation_count=db.query(Conversation).filter(Conversation.user_id == target.id).count(),
        message_count=db.query(Message).filter(Message.user_id == target.id).count(),
        query_log_count=db.query(QueryLog).filter(QueryLog.user_id == target.id).count(),
        storage_bytes=db.query(func.coalesce(func.sum(Document.size_bytes), 0))
        .filter(Document.user_id == target.id)
        .scalar()
        or 0,
        recent_documents=[_document_response(doc) for doc in recent_documents],
        recent_conversations=[
            RecentConversationItem(
                id=conversation.id,
                title=conversation.title,
                message_count=message_count or 0,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
            )
            for conversation, message_count in conversation_rows
        ],
    )


@router.patch("/users/{user_id}/status", response_model=AdminUserResponse)
def admin_set_user_status(
    user_id: int,
    payload: AdminUserStatusUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserResponse:
    target = _get_managed_user(db, user_id, admin)
    target.is_active = payload.is_active
    if not payload.is_active:
        # Banning kicks the user out immediately.
        db.query(DbSession).filter(DbSession.user_id == target.id).delete()
    db.commit()
    return _admin_user_response(target)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    settings = get_settings()
    target = _get_managed_user(db, user_id, admin)

    documents = db.query(Document).filter(Document.user_id == target.id).order_by(Document.id).all()
    errors: list[str] = []
    for document in documents:
        try:
            qdrant_indexer.QdrantIndexer(settings).delete_by_document(document.id)
        except Exception as exc:  # pragma: no cover - external service specific
            errors.append(f"qdrant: {type(exc).__name__}")
        try:
            neo4j_indexer.Neo4jIndexer(settings).delete_by_document(document.id)
        except Exception as exc:  # pragma: no cover - external service specific
            errors.append(f"neo4j: {type(exc).__name__}")
        try:
            StorageClient(settings).delete_object(document.storage_path)
        except Exception as exc:  # pragma: no cover - external service specific
            errors.append(f"storage: {type(exc).__name__}")

    # Explicit child deletes keep SQLite tests (FK enforcement off) consistent.
    db.query(SupportMessage).filter(SupportMessage.sender_id == target.id).delete(
        synchronize_session=False
    )
    db.query(SupportThread).filter(SupportThread.user_id == target.id).delete(
        synchronize_session=False
    )
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == target.id).delete(
        synchronize_session=False
    )
    db.query(QueryLog).filter(QueryLog.user_id == target.id).delete(synchronize_session=False)
    db.query(IngestionJob).filter(IngestionJob.user_id == target.id).delete(
        synchronize_session=False
    )
    db.query(Message).filter(Message.user_id == target.id).delete(synchronize_session=False)
    db.query(Conversation).filter(Conversation.user_id == target.id).delete(
        synchronize_session=False
    )
    db.query(DbSession).filter(DbSession.user_id == target.id).delete(synchronize_session=False)
    db.query(Document).filter(Document.user_id == target.id).delete(synchronize_session=False)
    db.delete(target)
    db.commit()

    if errors:  # pragma: no cover - external service specific
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"User deleted with partial store cleanup: {', '.join(errors)}",
        )


@router.get("/documents", response_model=AdminDocumentsResponse)
def admin_documents(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminDocumentsResponse:
    rows = (
        db.query(Document, User)
        .join(User, User.id == Document.user_id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return AdminDocumentsResponse(
        items=[
            AdminDocumentResponse(
                id=document.id,
                file_name=document.file_name,
                content_type=document.content_type,
                size_bytes=document.size_bytes,
                status=document.status,
                error=document.error,
                created_at=document.created_at,
                user_id=document.user_id,
                owner_email=owner.email,
                owner_full_name=owner.full_name,
            )
            for document, owner in rows
        ]
    )


@router.get("/ingestions", response_model=AdminIngestionsResponse)
def admin_ingestions(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminIngestionsResponse:
    jobs = db.query(IngestionJob).order_by(IngestionJob.id.desc()).all()
    return AdminIngestionsResponse(items=[_job_response(job) for job in jobs])


@router.get("/conversations", response_model=AdminConversationsResponse)
def admin_conversations(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminConversationsResponse:
    rows = (
        db.query(Conversation, User, func.count(Message.id))
        .join(User, User.id == Conversation.user_id)
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return AdminConversationsResponse(
        items=[
            AdminConversationItem(
                id=conversation.id,
                title=conversation.title,
                document_id=conversation.document_id,
                user_id=conversation.user_id,
                owner_email=owner.email,
                owner_full_name=owner.full_name,
                message_count=message_count or 0,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
            )
            for conversation, owner, message_count in rows
        ]
    )


@router.get("/messages", response_model=AdminMessagesResponse)
def admin_messages(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminMessagesResponse:
    rows = (
        db.query(Message, User, Conversation)
        .join(User, User.id == Message.user_id)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .order_by(Message.created_at.desc())
        .all()
    )
    return AdminMessagesResponse(
        items=[
            AdminMessageItem(
                id=message.id,
                conversation_id=message.conversation_id,
                conversation_title=conversation.title,
                user_id=message.user_id,
                owner_email=owner.email,
                role=message.role,
                content=message.content,
                confidence_score=message.confidence_score,
                web_search_used=message.web_search_used,
                created_at=message.created_at,
            )
            for message, owner, conversation in rows
        ]
    )


@router.get("/query-logs", response_model=AdminQueryLogsResponse)
def admin_query_logs(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminQueryLogsResponse:
    rows = (
        db.query(QueryLog, User)
        .join(User, User.id == QueryLog.user_id)
        .order_by(QueryLog.created_at.desc())
        .all()
    )
    return AdminQueryLogsResponse(
        items=[
            AdminQueryLogItem(
                id=log.id,
                user_id=log.user_id,
                owner_email=owner.email,
                query=log.query,
                answer=log.answer,
                confidence_score=log.confidence_score,
                web_search_used=log.web_search_used,
                retry_count=log.retry_count,
                latency_ms=log.latency_ms,
                created_at=log.created_at,
            )
            for log, owner in rows
        ]
    )


@router.get("/system", response_model=SystemStats)
def admin_system(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SystemStats:
    settings = get_settings()

    job_rows = db.query(IngestionJob.status, func.count()).group_by(IngestionJob.status).all()
    jobs_by_status = {status: int(count) for status, count in job_rows}

    qdrant_ready, qdrant_detail = qdrant_indexer.QdrantIndexer(settings).ready()
    neo4j_ready, neo4j_detail = neo4j_indexer.Neo4jIndexer(settings).ready()
    storage_ready, storage_detail = StorageClient(settings).ready()

    return SystemStats(
        users=db.query(User).count(),
        documents=db.query(Document).count(),
        ingestion_jobs=jobs_by_status,
        conversations=db.query(Conversation).count(),
        messages=db.query(Message).count(),
        query_logs=db.query(QueryLog).count(),
        dependencies=[
            _dependency_status("qdrant", qdrant_ready, qdrant_detail),
            _dependency_status("neo4j", neo4j_ready, neo4j_detail),
            _dependency_status("minio", storage_ready, storage_detail),
        ],
    )
