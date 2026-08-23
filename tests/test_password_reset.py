"""Offline tests for the forgot/reset password flow."""

from __future__ import annotations

import re
from typing import Any

from fastapi.testclient import TestClient


def _csrf(client: TestClient) -> str:
    return client.get("/api/v1/auth/csrf").json()["csrf_token"]


def _register(client: TestClient, email: str, password: str = "password123") -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "User"},
        headers={"X-CSRF-Token": _csrf(client)},
    )


def _capture_sent_email(monkeypatch: Any) -> list[str]:
    sent: list[str] = []
    from src.api.routers import auth as auth_router

    def fake_send_email(settings: Any, to_email: str, subject: str, html_body: str) -> bool:
        sent.append(html_body)
        return True

    monkeypatch.setattr(auth_router, "send_email", fake_send_email)
    return sent


def test_forgot_password_is_generic_for_unknown_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nobody@example.com"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 200
    assert "reset link" in response.json()["message"]


def test_full_password_reset_flow(client: TestClient, monkeypatch: Any) -> None:
    sent = _capture_sent_email(monkeypatch)
    _register(client, "resetme@example.com")

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "resetme@example.com"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 200
    match = re.search(r"token=([A-Za-z0-9_-]+)", sent[0])
    assert match is not None
    token = match.group(1)

    # The reset must work while logged out (fresh client without cookies).
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewPassword123!"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert reset.status_code == 200

    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "resetme@example.com", "password": "password123"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "resetme@example.com", "password": "NewPassword123!"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert new_login.status_code == 200


def test_reset_token_is_single_use(client: TestClient, monkeypatch: Any) -> None:
    sent = _capture_sent_email(monkeypatch)
    _register(client, "single@example.com")
    client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "single@example.com"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    match = re.search(r"token=([A-Za-z0-9_-]+)", sent[0])
    assert match is not None
    token = match.group(1)

    first = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewPassword123!"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "AnotherPass123!"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert second.status_code == 400


def test_reset_rejects_invalid_token(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "not-a-real-token-value", "new_password": "Whatever123!"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 400
