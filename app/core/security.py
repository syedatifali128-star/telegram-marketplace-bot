from __future__ import annotations

import hmac

from fastapi import Request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.config import settings

_serializer = URLSafeTimedSerializer(settings.secret_key, salt="dashboard-session")
SESSION_COOKIE = "dashboard_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 8  # 8 hours


def verify_credentials(username: str, password: str) -> bool:
    # constant-time comparisons to avoid trivial timing side-channels
    user_ok = hmac.compare_digest(username, settings.admin_username)
    pass_ok = hmac.compare_digest(password, settings.admin_password)
    return user_ok and pass_ok


def create_session_token(username: str) -> str:
    return _serializer.dumps({"username": username})


def read_session_token(token: str) -> str | None:
    try:
        data = _serializer.loads(token, max_age=SESSION_MAX_AGE_SECONDS)
        return data.get("username")
    except BadSignature:
        return None


def get_current_admin(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    return read_session_token(token)


class NotAuthenticated(Exception):
    """Raised by require_admin; caught by an app-level handler that redirects to /login."""


def require_admin(request: Request) -> str:
    """FastAPI dependency — raises NotAuthenticated if not logged in."""
    admin = get_current_admin(request)
    if admin is None:
        raise NotAuthenticated()
    return admin
