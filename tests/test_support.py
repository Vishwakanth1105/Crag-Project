"""Offline tests for the support ticket system (user + admin flows)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _csrf(client: TestClient) -> str:
    return client.get("/api/v1/auth/csrf").json()["csrf_token"]


def _register(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "User"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    return _login(client, email)


def _login(client: TestClient, email: str) -> dict[str, str]:
    """Authenticate as an existing user, returning a fresh CSRF header pair."""
    client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    return {"X-CSRF-Token": _csrf(client)}


def _make_admin(client: TestClient, email: str) -> dict[str, str]:
    headers = _register(client, email)
    from src.db.models import User
    from src.db.session import get_session_factory

    session = get_session_factory()()
    user = session.query(User).filter(User.email == email).first()
    user.role = "admin"
    session.commit()
    session.close()
    return headers


def _create_ticket_with_headers(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/support",
        json={"subject": "Login issue", "message": "I cannot log in."},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_user_creates_and_lists_own_tickets(client: TestClient) -> None:
    headers = _register(client, "ticketuser@example.com")
    ticket_id = _create_ticket_with_headers(client, headers)

    mine = client.get("/api/v1/support/mine", headers=headers)
    assert mine.status_code == 200
    items = mine.json()["items"]
    assert [t["id"] for t in items] == [ticket_id]
    assert items[0]["status"] == "open"
    assert items[0]["messages"][0]["sender_role"] == "user"


def test_tickets_are_private_between_users(client: TestClient) -> None:
    owner_headers = _register(client, "owner@example.com")
    ticket_id = _create_ticket_with_headers(client, owner_headers)

    other_headers = _register(client, "other@example.com")
    denied = client.get(f"/api/v1/support/{ticket_id}", headers=other_headers)
    assert denied.status_code == 403

    reply = client.post(
        f"/api/v1/support/{ticket_id}/messages",
        json={"content": "hijack"},
        headers=other_headers,
    )
    assert reply.status_code == 403

    mine = client.get("/api/v1/support/mine", headers=other_headers)
    assert mine.json()["items"] == []


def test_admin_full_lifecycle(client: TestClient) -> None:
    owner_headers = _register(client, "lifecycle@example.com")
    ticket_id = _create_ticket_with_headers(client, owner_headers)

    admin_headers = _make_admin(client, "supportadmin@example.com")

    listing = client.get("/api/v1/support/admin/threads", headers=admin_headers)
    assert listing.status_code == 200
    thread = next(t for t in listing.json()["items"] if t["id"] == ticket_id)
    assert thread["status"] == "open"
    assert thread["user_email"] == "lifecycle@example.com"

    detail = client.get(f"/api/v1/support/{ticket_id}", headers=admin_headers)
    assert detail.status_code == 200

    reply = client.post(
        f"/api/v1/support/{ticket_id}/messages",
        json={"content": "We are looking into it."},
        headers=admin_headers,
    )
    assert reply.status_code == 200

    after_reply = client.get(f"/api/v1/support/{ticket_id}", headers=owner_headers).json()
    assert after_reply["status"] == "pending"
    assert after_reply["messages"][-1]["sender_role"] == "admin"

    resolve = client.patch(
        f"/api/v1/support/admin/{ticket_id}/status",
        json={"status": "resolved"},
        headers=admin_headers,
    )
    assert resolve.status_code == 200

    # Switch back to the owner's identity; a user reply on a resolved ticket
    # reopens it.
    owner_headers = _login(client, "lifecycle@example.com")
    reopen = client.post(
        f"/api/v1/support/{ticket_id}/messages",
        json={"content": "Actually still broken."},
        headers=owner_headers,
    )
    assert reopen.status_code == 200
    reopened = client.get(f"/api/v1/support/{ticket_id}", headers=owner_headers).json()
    assert reopened["status"] == "open"


def test_admin_status_filter(client: TestClient) -> None:
    admin_headers = _make_admin(client, "filteradmin@example.com")
    _create_ticket_with_headers(client, admin_headers)

    resolved_filter = client.get(
        "/api/v1/support/admin/threads?status=resolved", headers=admin_headers
    )
    assert resolved_filter.status_code == 200
    assert all(t["status"] == "resolved" for t in resolved_filter.json()["items"])

    bad_filter = client.get("/api/v1/support/admin/threads?status=bogus", headers=admin_headers)
    assert bad_filter.status_code == 200


def test_non_admin_cannot_access_admin_endpoints(client: TestClient) -> None:
    headers = _register(client, "plainuser@example.com")
    listing = client.get("/api/v1/support/admin/threads", headers=headers)
    assert listing.status_code == 403

    patch = client.patch(
        "/api/v1/support/admin/1/status",
        json={"status": "resolved"},
        headers=headers,
    )
    assert patch.status_code == 403
