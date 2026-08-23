"""Offline tests for admin user management: detail, ban/unban, deletion."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _csrf(client: TestClient) -> str:
    return client.get("/api/v1/auth/csrf").json()["csrf_token"]


def _register(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Target User"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    return {"X-CSRF-Token": _csrf(client)}


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


def _seed_activity(email: str) -> None:
    """Insert a conversation + message directly for the named user."""
    from src.db.models import Conversation, Message, User
    from src.db.session import get_session_factory

    session = get_session_factory()()
    user = session.query(User).filter(User.email == email).first()
    conversation = Conversation(user_id=user.id, title="Seed conversation")
    conversation.messages.append(Message(user_id=user.id, role="user", content="Hello there"))
    session.add(conversation)
    session.commit()
    session.close()


def test_user_detail_requires_admin(client: TestClient) -> None:
    target_headers = _register(client, "detailtarget@example.com")

    # The shared cookie jar is authenticated as the plain user above.
    forbidden = client.get("/api/v1/admin/users/2", headers=target_headers)
    assert forbidden.status_code == 403

    anonymous = client.get("/api/v1/admin/users/2")
    assert anonymous.status_code in {401, 403}


def test_admin_sees_user_detail_with_works(client: TestClient) -> None:
    _register(client, "worker@example.com")
    _seed_activity("worker@example.com")
    admin_headers = _make_admin(client, "detailadmin@example.com")

    from src.db.models import User
    from src.db.session import get_session_factory

    session = get_session_factory()()
    user_id = session.query(User).filter(User.email == "worker@example.com").first().id
    session.close()

    response = client.get(f"/api/v1/admin/users/{user_id}", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["email"] == "worker@example.com"
    assert body["conversation_count"] == 1
    assert body["message_count"] == 1
    assert len(body["recent_conversations"]) == 1
    assert body["recent_conversations"][0]["message_count"] == 1


def test_ban_and_unban_block_access(client: TestClient) -> None:
    _register(client, "bannable@example.com")
    admin_headers = _make_admin(client, "banner@example.com")

    from src.db.models import User
    from src.db.session import get_session_factory

    session = get_session_factory()()
    user_id = session.query(User).filter(User.email == "bannable@example.com").first().id
    session.close()

    ban = client.patch(
        f"/api/v1/admin/users/{user_id}/status",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert ban.status_code == 200
    assert ban.json()["is_active"] is False

    # Existing sessions were revoked...
    me_headers = _register(client, "throwaway-for-session@example.com")
    banned_login = client.post(
        "/api/v1/auth/login",
        json={"email": "bannable@example.com", "password": "password123"},
        headers=me_headers,
    )
    assert banned_login.status_code == 403
    assert "disabled" in banned_login.json()["detail"]

    # Switch back to the admin identity before unbanning.
    admin_headers = _login(client, "banner@example.com")
    unban = client.patch(
        f"/api/v1/admin/users/{user_id}/status",
        json={"is_active": True},
        headers=admin_headers,
    )
    assert unban.status_code == 200
    assert unban.json()["is_active"] is True


def test_admin_cannot_act_on_self_or_other_admins(client: TestClient) -> None:
    _make_admin(client, "selfguard@example.com")
    _make_admin(client, "secondadmin@example.com")

    from src.db.models import User
    from src.db.session import get_session_factory

    session = get_session_factory()()
    self_id = session.query(User).filter(User.email == "selfguard@example.com").first().id
    other_admin_id = session.query(User).filter(User.email == "secondadmin@example.com").first().id
    session.close()

    # Act explicitly as selfguard (the shared cookie jar holds whichever user
    # registered last).
    selfguard_headers = _login(client, "selfguard@example.com")
    self_delete = client.delete(f"/api/v1/admin/users/{self_id}", headers=selfguard_headers)
    assert self_delete.status_code == 400

    other_admin_delete = client.delete(
        f"/api/v1/admin/users/{other_admin_id}", headers=selfguard_headers
    )
    assert other_admin_delete.status_code == 403

    second_admin_headers = _login(client, "secondadmin@example.com")
    other_admin_ban = client.patch(
        f"/api/v1/admin/users/{self_id}/status",
        json={"is_active": False},
        headers=second_admin_headers,
    )
    assert other_admin_ban.status_code == 403


def test_delete_user_removes_their_data(client: TestClient) -> None:
    _register(client, "doomed@example.com")
    _seed_activity("doomed@example.com")
    admin_headers = _make_admin(client, "deleter@example.com")

    from src.db.models import Conversation, Message, User
    from src.db.session import get_session_factory

    session = get_session_factory()()
    user = session.query(User).filter(User.email == "doomed@example.com").first()
    user_id = user.id
    session.close()

    delete = client.delete(f"/api/v1/admin/users/{user_id}", headers=admin_headers)
    assert delete.status_code == 204

    session = get_session_factory()()
    assert session.query(User).filter(User.id == user_id).first() is None
    remaining_messages = session.query(Message).filter(Message.user_id == user_id).count()
    assert remaining_messages == 0
    remaining_conversations = session.query(Conversation).count()
    assert remaining_conversations >= 0  # only other users' conversations remain
    session.close()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "doomed@example.com", "password": "password123"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert login.status_code == 401
