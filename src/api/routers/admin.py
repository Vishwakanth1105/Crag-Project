"""Administrative endpoints (require the admin role)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.auth.deps import require_admin
from src.config import get_settings
from src.db.models import Conversation, Document, IngestionJob, Message, QueryLog, User
from src.db.session import get_db
from src.ingestion import neo4j_indexer, qdrant_indexer
from src.schemas import (
    AdminDocumentsResponse,
    AdminIngestionsResponse,
    AdminUserResponse,
    AdminUsersResponse,
    DependencyStatus,
    DocumentResponse,
    IngestionJobResponse,
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


@router.get("/documents", response_model=AdminDocumentsResponse)
def admin_documents(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminDocumentsResponse:
    documents = db.query(Document).order_by(Document.created_at.desc()).all()
    return AdminDocumentsResponse(items=[_document_response(doc) for doc in documents])


@router.get("/ingestions", response_model=AdminIngestionsResponse)
def admin_ingestions(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminIngestionsResponse:
    jobs = db.query(IngestionJob).order_by(IngestionJob.id.desc()).all()
    return AdminIngestionsResponse(items=[_job_response(job) for job in jobs])


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
