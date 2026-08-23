"""Transactional email delivery via the Brevo HTTP API.

When ``BREVO_API_KEY`` (or ``BREVO_FROM_EMAIL``) is not configured, messages
are logged instead of delivered so local development and offline tests keep
working without external credentials.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from src.config import Settings
from src.logging_config import get_logger

logger = get_logger("email")

_BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"


def send_email(settings: Settings, to_email: str, subject: str, html_body: str) -> bool:
    """Send an email; returns True when actually delivered via Brevo."""
    if not settings.brevo_api_key or not settings.brevo_from_email:
        logger.warning(
            "Email delivery skipped (Brevo not configured). to=%s subject=%s body=%s",
            to_email,
            subject,
            html_body,
        )
        return False

    payload = json.dumps(
        {
            "sender": {"name": "Agentic RAG", "email": settings.brevo_from_email},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html_body,
        }
    ).encode("utf-8")

    request = urllib.request.Request(  # noqa: S310 - fixed https endpoint
        _BREVO_ENDPOINT,
        data=payload,
        method="POST",
        headers={
            "api-key": settings.brevo_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15):  # noqa: S310 - fixed https endpoint
            return True
    except (urllib.error.URLError, OSError) as exc:
        logger.error("Brevo delivery failed for %s: %s", to_email, exc)
        return False


def password_reset_email(reset_link: str) -> tuple[str, str]:
    """Build (subject, html) for a password reset message."""
    subject = "Reset your Agentic RAG password"
    html_body = f"""
    <p>Hello,</p>
    <p>We received a request to reset your password. Click the button below to
    choose a new one. The link is valid for 60 minutes and can be used once.</p>
    <p><a href="{reset_link}" style="display:inline-block;padding:10px 18px;
    background:#4f46e5;color:#ffffff;border-radius:8px;text-decoration:none;">
    Reset password</a></p>
    <p>If you did not request this, you can safely ignore this email.</p>
    """
    return subject, html_body
