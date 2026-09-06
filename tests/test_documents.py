"""Offline tests for document upload, ingestion worker, and cascade delete."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.db.models import Document, IngestionJob


class FakeStorage:
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
        self.objects: dict[str, bytes] = {}
        self.deleted: list[str] = []

    def upload_bytes(
        self, key: str, data: bytes, *, content_type: str = "application/octet-stream"
    ) -> None:
        del content_type
        self.objects[key] = data

    def download_bytes(self, key: str) -> bytes:
        return self.objects[key]

    def delete_object(self, key: str) -> None:
        self.deleted.append(key)
        self.objects.pop(key, None)

    def ready(self) -> tuple[bool, str | None]:
        return True, None


class FakeQdrant:
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
        self.deleted: list[str] = []

    def upsert_documents(self, documents, *, batch_size: int = 64) -> int:  # noqa: ANN001
        return len(documents)

    def delete_by_document(self, document_id: str) -> int:
        self.deleted.append(document_id)
        return 1


class FakeNeo4j:
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
        self.deleted: list[str] = []

    def index_documents(self, documents) -> int:  # noqa: ANN001
        return len(documents)

    def delete_by_document(self, document_id: str) -> int:
        self.deleted.append(document_id)
        return 1


def _auth(client: TestClient) -> dict[str, str]:
    client.get("/api/v1/auth/csrf")
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    client.post(
        "/api/v1/auth/register",
        json={"email": "doc@example.com", "password": "password123", "full_name": "Doc"},
        headers={"X-CSRF-Token": csrf},
    )
    return {"X-CSRF-Token": csrf}


def test_upload_queues_ingestion_job(client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    storage = FakeStorage()
    monkeypatch.setattr("src.ingestion.qdrant_indexer.QdrantIndexer", FakeQdrant)
    monkeypatch.setattr("src.ingestion.neo4j_indexer.Neo4jIndexer", FakeNeo4j)
    monkeypatch.setattr("src.api.routers.documents.StorageClient", lambda settings: storage)
    monkeypatch.setattr("src.worker.StorageClient", lambda settings: storage)

    headers = _auth(client)
    response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("sample.txt", b"Mars has two moons: Phobos and Deimos.", "text/plain")},
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    assert data["file_name"] == "sample.txt"
    assert storage.objects[f"documents/1/{data['id']}"] == b"Mars has two moons: Phobos and Deimos."

    listed = client.get("/api/v1/documents", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1


def test_upload_rejects_unsupported_type(client: TestClient) -> None:  # noqa: ANN001
    headers = _auth(client)
    response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("evil.exe", b"MZ...", "application/octet-stream")},
    )
    assert response.status_code == 400


def test_upload_rejects_oversized_file(client: TestClient) -> None:  # noqa: ANN001
    headers = _auth(client)
    response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("big.txt", b"x" * 21_000_000, "text/plain")},
    )
    assert response.status_code == 413


def test_upload_requires_authentication(client: TestClient) -> None:  # noqa: ANN001
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    response = client.post(
        "/api/v1/documents/upload",
        headers={"X-CSRF-Token": csrf},
        files={"file": ("sample.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 401


def test_worker_processes_job_and_updates_document(
    client: TestClient,
    monkeypatch,
    db_session_factory,  # noqa: ANN001
) -> None:
    storage = FakeStorage()
    monkeypatch.setattr("src.ingestion.qdrant_indexer.QdrantIndexer", FakeQdrant)
    monkeypatch.setattr("src.ingestion.neo4j_indexer.Neo4jIndexer", FakeNeo4j)
    monkeypatch.setattr("src.worker.StorageClient", lambda settings: storage)

    from src.config import get_settings
    from src.worker import drain

    session = db_session_factory()
    from src.db.models import User

    user = User(email="worker@example.com", password_hash="x", role="user")
    session.add(user)
    session.commit()
    document = Document(
        id="doc-123",
        user_id=user.id,
        file_name="sample.txt",
        storage_path="documents/1/doc-123",
    )
    session.add(document)
    session.flush()
    session.add(IngestionJob(document_id=document.id, user_id=user.id, status="queued"))
    session.commit()
    storage.objects["documents/1/doc-123"] = b"Jupiter has many moons."

    processed = drain(get_settings(), storage)
    assert processed == 1

    session.refresh(document)
    assert document.status == "ready"
    assert document.text_content == "Jupiter has many moons."

    job = session.query(IngestionJob).filter(IngestionJob.document_id == "doc-123").first()
    assert job is not None
    assert job.status == "done"
    assert job.child_chunks > 0
    assert job.parent_chunks > 0
    session.close()


def test_worker_marks_job_failed_on_parse_error(
    client: TestClient,
    monkeypatch,
    db_session_factory,  # noqa: ANN001
) -> None:
    storage = FakeStorage()
    monkeypatch.setattr("src.worker.StorageClient", lambda settings: storage)

    from src.config import get_settings
    from src.worker import drain

    session = db_session_factory()
    from src.db.models import User

    user = User(email="bad@example.com", password_hash="x", role="user")
    session.add(user)
    session.commit()
    document = Document(
        id="doc-bad",
        user_id=user.id,
        file_name="sample.pdf",
        storage_path="documents/1/doc-bad",
    )
    session.add(document)
    session.flush()
    session.add(IngestionJob(document_id=document.id, user_id=user.id, status="queued"))
    session.commit()
    storage.objects["documents/1/doc-bad"] = b"not a real pdf"

    drain(get_settings(), storage)

    session.refresh(document)
    assert document.status == "failed"
    job = session.query(IngestionJob).filter(IngestionJob.document_id == "doc-bad").first()
    assert job is not None
    assert job.status == "failed"
    assert job.error
    session.close()


def test_worker_does_not_resurrect_deleted_document(
    client: TestClient,
    monkeypatch,
    db_session_factory,  # noqa: ANN001
) -> None:
    storage = FakeStorage()
    monkeypatch.setattr("src.worker.StorageClient", lambda settings: storage)

    from src.config import get_settings
    from src.worker import drain

    session = db_session_factory()
    from src.db.models import User

    user = User(email="deleted@example.com", password_hash="x", role="user")
    session.add(user)
    session.commit()
    document = Document(
        id="doc-gone",
        user_id=user.id,
        file_name="sample.txt",
        storage_path="documents/1/doc-gone",
    )
    session.add(document)
    session.flush()
    session.add(IngestionJob(document_id=document.id, user_id=user.id, status="queued"))
    session.commit()
    storage.objects["documents/1/doc-gone"] = b"Jupiter has many moons."

    # Delete the document (ORM cascade removes its ingestion jobs too) before
    # the worker claims the job. The worker must never resurrect the row.
    session.delete(document)
    session.commit()

    processed = drain(get_settings(), storage)
    assert processed == 0

    assert session.query(Document).filter(Document.id == "doc-gone").first() is None
    assert (
        session.query(IngestionJob).filter(IngestionJob.document_id == "doc-gone").first() is None
    )
    session.close()


def test_worker_cleans_up_stores_for_document_deleted_while_indexing(
    client: TestClient,
    monkeypatch,
    db_session_factory,  # noqa: ANN001
) -> None:
    qdrant = FakeQdrant()
    neo4j = FakeNeo4j()
    monkeypatch.setattr("src.ingestion.qdrant_indexer.QdrantIndexer", lambda settings: qdrant)
    monkeypatch.setattr("src.ingestion.neo4j_indexer.Neo4jIndexer", lambda settings: neo4j)
    monkeypatch.setattr("src.worker.StorageClient", FakeStorage)

    from src.config import get_settings
    from src.worker import drain

    session = db_session_factory()
    from src.db.models import User

    user = User(email="mid@example.com", password_hash="x", role="user")
    session.add(user)
    session.commit()
    document = Document(
        id="doc-gone",
        user_id=user.id,
        file_name="sample.txt",
        storage_path="documents/1/doc-gone",
    )
    session.add(document)
    session.flush()
    session.add(IngestionJob(document_id=document.id, user_id=user.id, status="queued"))
    session.commit()

    # Storage wraps each fake download: delete the document row mid-ingestion,
    # exactly like a DELETE request racing with the indexing worker.
    storage = FakeStorage()
    storage.objects["documents/1/doc-gone"] = b"Jupiter has many moons."
    original_download = storage.download_bytes

    def deleting_download(key: str) -> bytes:
        deleter = db_session_factory()
        deleter.query(Document).filter(Document.id == "doc-gone").delete(
            synchronize_session=False
        )
        deleter.commit()
        deleter.close()
        return original_download(key)

    storage.download_bytes = deleting_download  # type: ignore[method-assign]

    processed = drain(get_settings(), storage)
    assert processed == 1

    assert qdrant.deleted == ["doc-gone"]
    assert neo4j.deleted == ["doc-gone"]

    after = db_session_factory()
    assert after.query(Document).filter(Document.id == "doc-gone").first() is None
    job = after.query(IngestionJob).filter(IngestionJob.document_id == "doc-gone").first()
    assert job.status == "failed"
    after.close()
    session.close()


def test_document_content_returns_stored_and_fallback_text(
    client: TestClient,
    monkeypatch,
    db_session_factory,  # noqa: ANN001
) -> None:
    storage = FakeStorage()
    monkeypatch.setattr("src.api.routers.documents.StorageClient", lambda settings: storage)

    headers = _auth(client)
    created = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("legacy.txt", b"Legacy fallback text.", "text/plain")},
    ).json()

    # No stored text yet -> endpoint falls back to decoding the stored file.
    response = client.get(f"/api/v1/documents/{created['id']}/content", headers=headers)
    assert response.status_code == 200
    assert response.json()["text"] == "Legacy fallback text."

    # Stored text wins once the worker has persisted it.
    session = db_session_factory()
    document = session.get(Document, created["id"])
    document.text_content = "Stored full text."
    session.commit()
    session.close()

    stored = client.get(f"/api/v1/documents/{created['id']}/content", headers=headers)
    assert stored.json()["text"] == "Stored full text."


def test_document_content_is_owner_scoped(client: TestClient) -> None:  # noqa: ANN001
    headers = _auth(client)
    other = client.get("/api/v1/documents").json()
    del other
    response = client.get("/api/v1/documents/does-not-exist/content", headers=headers)
    assert response.status_code == 404


def test_delete_cascades_across_stores(
    client: TestClient,
    monkeypatch,
    db_session_factory,  # noqa: ANN001
) -> None:
    storage = FakeStorage()
    qdrant = FakeQdrant()
    neo4j = FakeNeo4j()
    monkeypatch.setattr("src.ingestion.qdrant_indexer.QdrantIndexer", lambda settings: qdrant)
    monkeypatch.setattr("src.ingestion.neo4j_indexer.Neo4jIndexer", lambda settings: neo4j)
    monkeypatch.setattr("src.api.routers.documents.StorageClient", lambda settings: storage)

    headers = _auth(client)
    created = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("delete.txt", b"content to delete", "text/plain")},
    ).json()

    response = client.delete(f"/api/v1/documents/{created['id']}", headers=headers)
    assert response.status_code == 204
    assert qdrant.deleted == [created["id"]]
    assert neo4j.deleted == [created["id"]]
    assert storage.deleted == [f"documents/1/{created['id']}"]

    assert client.get(f"/api/v1/documents/{created['id']}", headers=headers).status_code == 404

    session = db_session_factory()
    assert session.query(Document).filter(Document.id == created["id"]).first() is None
    assert (
        session.query(IngestionJob).filter(IngestionJob.document_id == created["id"]).first()
        is None
    )
    session.close()
