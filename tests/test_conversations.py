"""Offline tests for conversations and messages."""

from __future__ import annotations

from fastapi.testclient import TestClient
from langchain_core.documents import Document

from src.db.models import Message, QueryLog


def _stub_run_agent(query: str) -> dict:
    return {
        "generation": f"Answer about {query}",
        "confidence_score": 0.85,
        "sources": ["sample.md"],
        "web_search_used": False,
        "retry_count": 1,
        "retrieval_trace": ["grade: 1/1 relevant"],
        "documents": [
            Document(
                page_content="Mars has two moons: Phobos and Deimos.",
                metadata={
                    "document_id": "doc-123",
                    "file_name": "sample.md",
                    "score": 0.91,
                    "retrieval_source": "vector",
                },
            ),
            Document(
                page_content="Graph fact: Mars HAS_MOON Phobos.",
                metadata={
                    "document_id": None,
                    "retrieval_source": "graph",
                    "score": 0.5,
                },
            ),
            Document(page_content="   ", metadata={}),
        ],
    }


def _register(client: TestClient, email: str) -> dict[str, str]:
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "User"},
        headers={"X-CSRF-Token": csrf},
    )
    return {"X-CSRF-Token": csrf}


def _conversation(
    client: TestClient, headers: dict[str, str], title: str = "New conversation"
) -> int:
    response = client.post(
        "/api/v1/conversations",
        json={"title": title},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_and_list_conversations(client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    headers = _register(client, "conv@example.com")
    conversation_id = _conversation(client, headers, title="Mars facts")

    listed = client.get("/api/v1/conversations", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["items"][0]["title"] == "Mars facts"
    assert listed.json()["items"][0]["id"] == conversation_id


def test_send_message_persists_user_and_assistant_messages(
    client: TestClient,
    monkeypatch,
    db_session_factory,  # noqa: ANN001
) -> None:
    monkeypatch.setattr("src.services.conversations.run_agent", _stub_run_agent)
    headers = _register(client, "chat@example.com")
    conversation_id = _conversation(client, headers)

    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "What are the moons of Mars?"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "assistant"
    assert data["content"] == "Answer about What are the moons of Mars?"
    assert data["confidence_score"] == 0.85
    assert data["sources"] == ["sample.md"]
    assert data["trace"] == ["grade: 1/1 relevant"]
    evidence = data["retrieval_evidence"]
    assert len(evidence) == 2
    assert evidence[0]["document_id"] == "doc-123"
    assert evidence[0]["file_name"] == "sample.md"
    assert "Phobos" in evidence[0]["text"]
    assert evidence[1]["retrieval_source"] == "graph"

    messages = client.get(
        f"/api/v1/conversations/{conversation_id}/messages", headers=headers
    ).json()["items"]
    assert [message["role"] for message in messages] == ["user", "assistant"]
    stored_evidence = messages[-1]["retrieval_evidence"]
    assert stored_evidence and stored_evidence[0]["document_id"] == "doc-123"

    session = db_session_factory()
    assert session.query(Message).count() == 2
    assert session.query(QueryLog).count() == 1
    assert session.query(QueryLog).first().retry_count == 1
    session.close()


def test_send_message_validates_empty_content(client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr("src.services.conversations.run_agent", _stub_run_agent)
    headers = _register(client, "empty@example.com")
    conversation_id = _conversation(client, headers)
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": ""},
        headers=headers,
    )
    assert response.status_code == 422


def test_conversation_is_owner_scoped(client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr("src.services.conversations.run_agent", _stub_run_agent)
    alice = _register(client, "alice2@example.com")
    conversation_id = _conversation(client, alice)

    from fastapi.testclient import TestClient as TC

    from src.api.app import app

    bob_client = TC(app)
    _register(bob_client, "bob2@example.com")
    bob_csrf = bob_client.get("/api/v1/auth/csrf").json()["csrf_token"]
    bob_headers = {"X-CSRF-Token": bob_csrf}

    assert bob_client.get(f"/api/v1/conversations/{conversation_id}").status_code == 404
    assert (
        bob_client.delete(
            f"/api/v1/conversations/{conversation_id}", headers=bob_headers
        ).status_code
        == 404
    )
    assert (
        bob_client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"content": "hi"},
            headers=bob_headers,
        ).status_code
        == 404
    )

    assert client.get(f"/api/v1/conversations/{conversation_id}", headers=alice).status_code == 200


def test_delete_conversation_cascades_messages(
    client: TestClient,
    monkeypatch,
    db_session_factory,  # noqa: ANN001
) -> None:
    monkeypatch.setattr("src.services.conversations.run_agent", _stub_run_agent)
    headers = _register(client, "delete@example.com")
    conversation_id = _conversation(client, headers)
    client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "hello"},
        headers=headers,
    )

    response = client.delete(f"/api/v1/conversations/{conversation_id}", headers=headers)
    assert response.status_code == 204

    session = db_session_factory()
    assert session.query(Message).count() == 0
    session.close()
