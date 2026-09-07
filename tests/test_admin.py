"""Offline tests for admin endpoints and legacy endpoint removal."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _register(client: TestClient, email: str, password: str) -> dict[str, str]:
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "User"},
        headers={"X-CSRF-Token": csrf},
    )
    return {"X-CSRF-Token": client.get("/api/v1/auth/csrf").json()["csrf_token"]}


def _make_admin(client: TestClient, email: str, password: str) -> dict[str, str]:
    headers = _register(client, email, password)
    from src.db.models import User
    from src.db.session import get_session_factory

    session = get_session_factory()()
    user = session.query(User).filter(User.email == email).first()
    user.role = "admin"
    session.commit()
    session.close()
    return headers


def test_admin_requires_admin_role(client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    headers = _register(client, "regular@example.com", "password123")
    assert client.get("/api/v1/admin/users", headers=headers).status_code == 403


def test_admin_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/admin/users")
    assert response.status_code == 401


def test_admin_users_lists_all(client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    _register(client, "someone@example.com", "password123")
    headers = _make_admin(client, "admin@example.com", "password123")

    response = client.get("/api/v1/admin/users", headers=headers)
    assert response.status_code == 200
    emails = {user["email"] for user in response.json()["items"]}
    assert {"admin@example.com", "someone@example.com"} <= emails


def test_admin_system_stats(client: TestClient, monkeypatch, db_session_factory) -> None:  # noqa: ANN001
    headers = _make_admin(client, "sys@example.com", "password123")
    response = client.get("/api/v1/admin/system", headers=headers)
    assert response.status_code == 200
    stats = response.json()
    assert stats["users"] >= 1
    assert stats["documents"] == 0
    assert isinstance(stats["ingestion_jobs"], dict)


def _user_id(email: str) -> int:
    from src.db.models import User
    from src.db.session import get_session_factory

    session = get_session_factory()()
    user = session.query(User).filter(User.email == email).first()
    assert user is not None
    user_id = user.id
    session.close()
    return user_id


def _seed_document(db_session_factory, owner_email: str, file_name: str) -> str:
    session = db_session_factory()
    from src.db.models import Document

    document = Document(
        user_id=_user_id(owner_email),
        file_name=file_name,
        content_type="text/plain",
        size_bytes=12,
        storage_path="test/path.txt",
        content_hash="abc",
        status="indexed",
    )
    session.add(document)
    session.commit()
    document_id = document.id
    session.close()
    return document_id


def _seed_conversation(db_session_factory, owner_email: str, title: str) -> int:
    session = db_session_factory()
    from src.db.models import Conversation, Message

    conversation = Conversation(user_id=_user_id(owner_email), title=title)
    session.add(conversation)
    session.commit()
    session.add(
        Message(
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            role="user",
            content="Question one",
        )
    )
    session.add(
        Message(
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            role="assistant",
            content="Answer one",
            confidence_score=0.87,
        )
    )
    session.commit()
    conversation_id = conversation.id
    session.close()
    return conversation_id


def _seed_query_log(db_session_factory, owner_email: str) -> int:
    session = db_session_factory()
    from src.db.models import QueryLog

    log = QueryLog(
        user_id=_user_id(owner_email),
        query="What is the sky?",
        answer="The sky is blue.",
        confidence_score=0.62,
        web_search_used=True,
        retry_count=1,
        latency_ms=1540,
    )
    session.add(log)
    session.commit()
    log_id = log.id
    session.close()
    return log_id


def test_admin_documents_includes_owner(client, db_session_factory, monkeypatch) -> None:  # noqa: ANN001
    _register(client, "docowner@example.com", "password123")
    headers = _make_admin(client, "docadmin@example.com", "password123")
    created_id = _seed_document(db_session_factory, "docowner@example.com", "report.txt")

    response = client.get("/api/v1/admin/documents", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["id"] == created_id
    assert item["file_name"] == "report.txt"
    assert item["owner_email"] == "docowner@example.com"
    assert item["user_id"] == _user_id("docowner@example.com")


def test_admin_conversations_with_message_counts(client, db_session_factory, monkeypatch) -> None:  # noqa: ANN001
    _register(client, "convowner@example.com", "password123")
    headers = _make_admin(client, "convadmin@example.com", "password123")
    created_id = _seed_conversation(db_session_factory, "convowner@example.com", "Deep dive")

    response = client.get("/api/v1/admin/conversations", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["id"] == created_id
    assert item["title"] == "Deep dive"
    assert item["owner_email"] == "convowner@example.com"
    assert item["message_count"] == 2


def test_admin_messages_lists_all(client, db_session_factory, monkeypatch) -> None:  # noqa: ANN001
    _register(client, "msgowner@example.com", "password123")
    headers = _make_admin(client, "msgadmin@example.com", "password123")
    _seed_conversation(db_session_factory, "msgowner@example.com", "Thread")

    response = client.get("/api/v1/admin/messages", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    assistant = next(item for item in items if item["role"] == "assistant")
    assert assistant["conversation_title"] == "Thread"
    assert assistant["owner_email"] == "msgowner@example.com"
    assert assistant["content"] == "Answer one"
    assert assistant["confidence_score"] == 0.87


def test_admin_query_logs_lists_all(client, db_session_factory, monkeypatch) -> None:  # noqa: ANN001
    _register(client, "qowner@example.com", "password123")
    headers = _make_admin(client, "qadmin@example.com", "password123")
    created_id = _seed_query_log(db_session_factory, "qowner@example.com")

    response = client.get("/api/v1/admin/query-logs", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["id"] == created_id
    assert item["query"] == "What is the sky?"
    assert item["answer"] == "The sky is blue."
    assert item["confidence_score"] == 0.62
    assert item["web_search_used"] is True
    assert item["latency_ms"] == 1540
    assert item["owner_email"] == "qowner@example.com"


def test_admin_records_require_admin_role(client: TestClient) -> None:
    headers = _register(client, "plainuser@example.com", "password123")
    for path in ("/api/v1/admin/documents", "/api/v1/admin/conversations",
                 "/api/v1/admin/messages", "/api/v1/admin/query-logs"):
        assert client.get(path, headers=headers).status_code == 403


def test_legacy_query_and_ingest_removed(client: TestClient) -> None:
    response = client.post(
        "/query",
        json={"query": "hello"},
        headers={"X-CSRF-Token": client.get("/api/v1/auth/csrf").json()["csrf_token"]},
    )
    assert response.status_code == 404

    response = client.post(
        "/ingest",
        json={"path": "/data/sample.md"},
        headers={"X-CSRF-Token": client.get("/api/v1/auth/csrf").json()["csrf_token"]},
    )
    assert response.status_code == 404
