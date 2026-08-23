"""Background ingestion worker.

Consumes ``queued`` rows from the ``ingestion_jobs`` table and performs
parse -> Qdrant upsert -> Neo4j graph index, marking the job and document
``done`` or ``failed``.

Each job is claimed and processed within a single session so status writes
persist atomically; jobs left ``running`` by a crashed worker are reclaimed
after a grace period.

Run via ``python -m src.worker`` (the ``worker`` compose service).
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from src.config import Settings, get_settings
from src.db.models import Document, IngestionJob
from src.db.session import get_session_factory
from src.ingestion import neo4j_indexer, qdrant_indexer
from src.ingestion.parser import ParsedDocument, parse_document
from src.logging_config import configure_logging, get_logger
from src.storage.minio_client import StorageClient

logger = get_logger("worker")

MAX_JOBS_PER_CYCLE = 4
POLL_INTERVAL_SECONDS = 2
STALE_RUNNING_MINUTES = 15
HEARTBEAT_FILE = Path(os.environ.get("WORKER_HEARTBEAT_FILE", "/data/worker.heartbeat"))


def _write_heartbeat() -> None:
    try:
        HEARTBEAT_FILE.write_text(str(time.time()))
    except OSError:
        logger.warning("could not write worker heartbeat", exc_info=True)


def _rekey_documents(parsed: ParsedDocument, document_id: str, file_name: str) -> None:
    """Bind chunk payloads to the application document id and user-facing name."""
    for document in parsed.parent_documents + parsed.child_documents:
        document.metadata["document_id"] = document_id
        document.metadata["source"] = file_name
        document.metadata["file_name"] = file_name


def _reclaim_stale_jobs(db: Session) -> None:
    cutoff = datetime.now(UTC) - timedelta(minutes=STALE_RUNNING_MINUTES)
    stale = (
        db.query(IngestionJob)
        .filter(IngestionJob.status == "running", IngestionJob.started_at < cutoff)
        .all()
    )
    for job in stale:
        job.status = "queued"
    if stale:
        db.commit()
        logger.warning("reclaimed %d stale running job(s)", len(stale))


def process_job(db: Session, job: IngestionJob, settings: Settings, storage: StorageClient) -> None:
    document = db.get(Document, job.document_id)
    if document is None:
        job.status = "failed"
        job.error = "document missing"
        return

    try:
        data = storage.download_bytes(document.storage_path)
        suffix = Path(document.file_name).suffix.lower()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp:
            temp.write(data)
            temp_path = temp.name
        try:
            parsed = parse_document(temp_path, settings)
        finally:
            Path(temp_path).unlink(missing_ok=True)
        _rekey_documents(parsed, document.id, document.file_name)

        qdrant_indexer.QdrantIndexer(settings).upsert_documents(parsed.child_documents)
        relationships = neo4j_indexer.Neo4jIndexer(settings).index_documents(
            parsed.parent_documents
        )

        document.status = "ready"
        document.error = None
        document.content_hash = hashlib.sha256(data).hexdigest()
        document.text_content = parsed.full_text[:1_000_000] or None
        job.parent_chunks = len(parsed.parent_documents)
        job.child_chunks = len(parsed.child_documents)
        job.graph_relationships = relationships
        job.status = "done"
        job.error = None
    except Exception as exc:
        db.rollback()
        logger.exception("ingestion job %s failed", job.id)
        document.status = "failed"
        document.error = str(exc)
        job.status = "failed"
        job.error = str(exc)
    finally:
        job.finished_at = datetime.now(UTC)


def drain(settings: Settings, storage: StorageClient) -> int:
    db = get_session_factory()()
    processed = 0
    try:
        _reclaim_stale_jobs(db)
        while processed < MAX_JOBS_PER_CYCLE:
            job = (
                db.query(IngestionJob)
                .filter(IngestionJob.status == "queued")
                .order_by(IngestionJob.id.asc())
                .first()
            )
            if job is None:
                break
            job.status = "running"
            job.started_at = datetime.now(UTC)
            db.flush()
            process_job(db, job, settings, storage)
            db.commit()
            processed += 1
    finally:
        db.close()
    return processed


def main() -> None:
    configure_logging()
    settings = get_settings()
    storage = StorageClient(settings)
    logger.info("worker started")
    while True:
        try:
            drain(settings, storage)
        except Exception:
            logger.exception("worker cycle failed")
        _write_heartbeat()
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
