"""Offline tests for CORS hardening.

The UI is always served same-origin with the API (Vite dev proxy in
development, nginx reverse proxy in production), so cross-origin access is
denied unless ``CORS_ORIGINS`` explicitly lists origins.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_cross_origin_request_gets_no_cors_headers(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "http://evil.example"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_preflight_from_unknown_origin_is_rejected(client: TestClient) -> None:
    response = client.options(
        "/api/v1/auth/csrf",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers
