"""Document upload, listing, detail, content, and deletion (owner-scoped)."""

from __future__ import annotations

import hashlib
import io
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pypdf import PdfReader
from sqlalchemy.orm import Session

from src.auth.deps import get_current_user
from src.config import Settings, get_settings
from src.db.models import Document, IngestionJob, User
from src.db.session import get_db
from src.ingestion import neo4j_indexer, qdrant_indexer
from src.ingestion.parser import SUPPORTED_EXTENSIONS
from src.schemas import (
    DocumentContentResponse,
    DocumentListResponse,
    DocumentResponse,
)
from src.storage.minio_client import StorageClient

router = APIRouter(prefix="/documents")


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


def _get_owned_document(db: Session, document_id: str, user: User) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    settings = get_settings()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    content = await file.read(settings.upload_max_bytes + 1)
    if len(content) > settings.upload_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File exceeds the maximum allowed size",
        )
    if not content.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty")

    document_id = str(uuid.uuid4())
    storage_path = f"documents/{user.id}/{document_id}"
    storage = StorageClient(settings)
    try:
        storage.upload_bytes(
            storage_path,
            content,
            content_type=file.content_type or "application/octet-stream",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Upload storage unavailable"
        ) from exc

    document = Document(
        id=document_id,
        user_id=user.id,
        file_name=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        storage_path=storage_path,
        content_hash=hashlib.sha256(content).hexdigest(),
        status="pending",
    )
    db.add(document)
    db.flush()
    db.add(IngestionJob(document_id=document.id, user_id=user.id, status="queued"))
    db.commit()
    return _document_response(document)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    documents = (
        db.query(Document)
        .filter(Document.user_id == user.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return DocumentListResponse(items=[_document_response(doc) for doc in documents])


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    return _document_response(_get_owned_document(db, document_id, user))


def _extract_text_fallback(document: Document, settings: Settings) -> str | None:
    """Best-effort text for documents ingested before text persistence."""
    suffix = Path(document.file_name).suffix.lower()
    try:
        data = StorageClient(settings).download_bytes(document.storage_path)
        if suffix == ".pdf":
            reader = PdfReader(io.BytesIO(data))
            return "\n\n".join((page.extract_text() or "") for page in reader.pages) or None
        if suffix in {".txt", ".md"}:
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return data.decode("utf-8", errors="ignore")
    except Exception:  # pragma: no cover - external service specific
        return None
    return None


@router.get("/{document_id}/content", response_model=DocumentContentResponse)
def get_document_content(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentContentResponse:
    settings = get_settings()
    document = _get_owned_document(db, document_id, user)
    text = document.text_content or _extract_text_fallback(document, settings)
    return DocumentContentResponse(
        document_id=document.id,
        file_name=document.file_name,
        text=text,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    settings = get_settings()
    document = _get_owned_document(db, document_id, user)

    errors: list[str] = []
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

    db.query(IngestionJob).filter(IngestionJob.document_id == document.id).delete()
    db.delete(document)
    db.commit()
    if errors:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Document deleted with partial store cleanup: {', '.join(errors)}",
        )
