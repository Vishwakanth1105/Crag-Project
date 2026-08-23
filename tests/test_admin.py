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
