from datetime import datetime, timedelta, timezone
import secrets
from threading import Lock

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings

_bearer = HTTPBearer(auto_error=False)
_tokens: dict[str, datetime] = {}
_tokens_lock = Lock()


def issue_admin_token(username: str, password: str) -> tuple[str, int]:
    settings = get_settings()
    if not settings.admin_username or not settings.admin_password:
        raise HTTPException(status_code=503, detail="Admin authentication is not configured.")
    if not secrets.compare_digest(username, settings.admin_username) or not secrets.compare_digest(password, settings.admin_password):
        raise HTTPException(status_code=401, detail="Invalid admin credentials.")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.admin_token_ttl_seconds)
    with _tokens_lock:
        _tokens[token] = expires_at
        expired = [value for value, expiry in _tokens.items() if expiry <= datetime.now(timezone.utc)]
        for value in expired:
            del _tokens[value]
    return token, settings.admin_token_ttl_seconds


def get_admin_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin authentication required.")
    with _tokens_lock:
        expires_at = _tokens.get(credentials.credentials)
        if expires_at is None or expires_at <= datetime.now(timezone.utc):
            _tokens.pop(credentials.credentials, None)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired admin token.")
    return get_settings().admin_username