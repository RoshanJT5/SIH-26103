from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from threading import Lock
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings

_bearer = HTTPBearer(auto_error=False)
_tokens: dict[str, datetime] = {}
_user_sessions: dict[str, dict[str, Any]] = {}
_tokens_lock = Lock()

# In-memory user registry for official officers and admins
_registered_users: dict[str, dict[str, str]] = {
    "officer@gov.in": {
        "name": "Nodal Project Officer",
        "email": "officer@gov.in",
        "username": "nodal_officer",
        "password_hash": hashlib.sha256("officer123".encode()).hexdigest(),
        "role": "officer",
    },
    "monitoring@sameeksha.gov.in": {
        "name": "Monitoring Director",
        "email": "monitoring@sameeksha.gov.in",
        "username": "monitoring_dir",
        "password_hash": hashlib.sha256("monitor123".encode()).hexdigest(),
        "role": "director",
    },
}


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def issue_admin_token(username: str, password: str) -> tuple[str, int]:
    settings = get_settings()
    if not settings.admin_username or not settings.admin_password:
        raise HTTPException(status_code=503, detail="Admin authentication is not configured.")
    if not secrets.compare_digest(username, settings.admin_username) or not secrets.compare_digest(password, settings.admin_password):
        raise HTTPException(status_code=401, detail="Invalid admin credentials.")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.admin_token_ttl_seconds)
    admin_profile = {
        "name": "System Administrator",
        "email": "admin@gov.in",
        "username": settings.admin_username,
        "role": "admin",
    }
    with _tokens_lock:
        _tokens[token] = expires_at
        _user_sessions[token] = {"user": admin_profile, "expires_at": expires_at}
        _cleanup_expired_tokens()
    return token, settings.admin_token_ttl_seconds


def register_user(name: str, email: str, password: str, username: str | None = None) -> tuple[str, int, dict[str, str]]:
    clean_email = email.strip().lower()
    clean_name = name.strip()
    clean_username = (username or clean_name.replace(" ", "_").lower()).strip()
    pwd_hash = _hash_password(password)

    user_record = {
        "name": clean_name,
        "email": clean_email,
        "username": clean_username,
        "password_hash": pwd_hash,
        "role": "officer",
    }

    token = secrets.token_urlsafe(32)
    ttl = get_settings().admin_token_ttl_seconds or 86400
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

    user_public = {
        "name": clean_name,
        "email": clean_email,
        "username": clean_username,
        "role": "officer",
    }

    with _tokens_lock:
        _registered_users[clean_email] = user_record
        _tokens[token] = expires_at
        _user_sessions[token] = {"user": user_public, "expires_at": expires_at}
        _cleanup_expired_tokens()

    return token, ttl, user_public


def authenticate_user(username_or_email: str, password: str) -> tuple[str, int, dict[str, str]]:
    settings = get_settings()
    identifier = username_or_email.strip()

    # 1. Check admin credentials
    if settings.admin_username and settings.admin_password:
        if secrets.compare_digest(identifier, settings.admin_username):
            if secrets.compare_digest(password, settings.admin_password):
                token, ttl = issue_admin_token(identifier, password)
                admin_profile = {
                    "name": "System Administrator",
                    "email": "admin@gov.in",
                    "username": settings.admin_username,
                    "role": "admin",
                }
                return token, ttl, admin_profile
            raise HTTPException(status_code=401, detail="Invalid admin credentials.")

    # 2. Check registered users
    clean_id = identifier.lower()
    pwd_hash = _hash_password(password)
    target_user: dict[str, str] | None = None

    with _tokens_lock:
        for u_email, u_data in _registered_users.items():
            if u_email.lower() == clean_id or u_data.get("username", "").lower() == clean_id:
                if u_data.get("password_hash") == pwd_hash:
                    target_user = u_data
                    break
                else:
                    raise HTTPException(status_code=401, detail="Invalid password.")

    if target_user is not None:
        token = secrets.token_urlsafe(32)
        ttl = settings.admin_token_ttl_seconds or 86400
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        user_public = {
            "name": target_user["name"],
            "email": target_user["email"],
            "username": target_user["username"],
            "role": target_user.get("role", "officer"),
        }
        with _tokens_lock:
            _tokens[token] = expires_at
            _user_sessions[token] = {"user": user_public, "expires_at": expires_at}
            _cleanup_expired_tokens()
        return token, ttl, user_public

    # 3. For official prototype demo: if email format and valid password, create on first login
    if "@" in identifier and len(password) >= 4:
        fallback_name = identifier.split("@")[0].replace(".", " ").replace("_", " ").title()
        return register_user(name=fallback_name, email=identifier, password=password)

    raise HTTPException(status_code=401, detail="Invalid credentials.")


def _cleanup_expired_tokens() -> None:
    now = datetime.now(timezone.utc)
    expired_tokens = [t for t, exp in _tokens.items() if exp <= now]
    for t in expired_tokens:
        _tokens.pop(t, None)
        _user_sessions.pop(t, None)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please login or signup to access this resource.",
        )
    with _tokens_lock:
        session = _user_sessions.get(credentials.credentials)
        if session is not None:
            if session["expires_at"] <= datetime.now(timezone.utc):
                _user_sessions.pop(credentials.credentials, None)
                _tokens.pop(credentials.credentials, None)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session expired. Please login again.",
                )
            return session["user"]

        # Check fallback in _tokens
        expires_at = _tokens.get(credentials.credentials)
        if expires_at is None or expires_at <= datetime.now(timezone.utc):
            _tokens.pop(credentials.credentials, None)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token.",
            )

        # Fallback admin user
        return {
            "name": "System Administrator",
            "email": "admin@gov.in",
            "username": get_settings().admin_username or "admin",
            "role": "admin",
        }


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any] | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None


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