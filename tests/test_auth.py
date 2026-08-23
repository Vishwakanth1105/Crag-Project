"""Offline tests for the auth flow (SQLite-backed)."""

from __future__ import annotations

from fastapi.testclient import TestClient

REGISTER_PAYLOAD = {
    "email": "alice@example.com",
    "password": "password123",
    "full_name": "Alice",
}


def _csrf(client: TestClient) -> str:
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    return response.json()["csrf_token"]


def _csrf_headers(client: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": _csrf(client)}


def test_csrf_endpoint_sets_cookie(client: TestClient) -> None:
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    assert response.json()["csrf_token"]
    assert "rag_csrf" in response.cookies


def test_register_requires_csrf(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 403


def test_register_rejects_mismatched_csrf(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json=REGISTER_PAYLOAD,
        headers={"X-CSRF-Token": "wrong-token"},
    )
    assert response.status_code == 403


def test_register_login_logout_flow(client: TestClient) -> None:
    registered = client.post(
        "/api/v1/auth/register", json=REGISTER_PAYLOAD, headers=_csrf_headers(client)
    )
    assert registered.status_code == 201
    assert registered.json()["role"] == "user"
    assert "rag_session" in registered.cookies

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"

    logged_out = client.post("/api/v1/auth/logout", headers=_csrf_headers(client))
    assert logged_out.status_code == 204

    after = client.get("/api/v1/auth/me")
    assert after.status_code == 401


def test_register_duplicate_email_conflicts(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD, headers=_csrf_headers(client))
    response = client.post(
        "/api/v1/auth/register", json=REGISTER_PAYLOAD, headers=_csrf_headers(client)
    )
    assert response.status_code == 409


def test_login_wrong_password_rejected(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD, headers=_csrf_headers(client))
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "not-the-password"},
        headers=_csrf_headers(client),
    )
    assert response.status_code == 401


def test_login_success_sets_session(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD, headers=_csrf_headers(client))
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
        headers=_csrf_headers(client),
    )
    assert response.status_code == 200
    assert "rag_session" in response.cookies
    assert client.get("/api/v1/auth/me").json()["email"] == "alice@example.com"


def test_short_password_rejected_by_validation(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "bob@example.com", "password": "short"},
        headers=_csrf_headers(client),
    )
    assert response.status_code == 422


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
