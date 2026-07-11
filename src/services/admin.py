"""Admin authentication — cookie-based session with CSRF protection."""

import hashlib
import hmac
import logging
import secrets

from fastapi import Request

from src.config import settings

log = logging.getLogger(__name__)

SESSION_COOKIE = "admin_session"
CSRF_COOKIE = "csrf_token"
SESSION_MAX_AGE = 86400 * 7  # 7 days


def make_session_value() -> str:
    """Create a signed session token from admin credentials."""
    data = f"{settings.ADMIN_USERNAME}:{settings.ADMIN_PASSWORD}"
    sig = hmac.new(
        settings.ADMIN_PASSWORD.encode(),
        data.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{settings.ADMIN_USERNAME}:{sig}"


def validate_session(value: str | None) -> bool:
    """Validate a session cookie value."""
    if not value:
        return False
    try:
        username, sig = value.split(":", 1)
        expected = make_session_value()
        exp_user, exp_sig = expected.split(":", 1)
        return (
            hmac.compare_digest(username, exp_user)
            and hmac.compare_digest(sig, exp_sig)
        )
    except (ValueError, AttributeError):
        return False


def get_admin_user(request: Request) -> str | None:
    """Return username if authenticated, else None."""
    session = request.cookies.get(SESSION_COOKIE)
    if session and validate_session(session):
        return settings.ADMIN_USERNAME
    return None


def generate_csrf_token() -> str:
    """Generate a random CSRF token."""
    return secrets.token_hex(32)


def validate_csrf_token(request: Request, form_token: str) -> bool:
    """Validate CSRF token from form against cookie."""
    cookie_token = request.cookies.get(CSRF_COOKIE)
    if not cookie_token or not form_token:
        return False
    return hmac.compare_digest(cookie_token, form_token)
