from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from threading import Lock
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func
from sqlalchemy.orm import Session

from .config import get_settings
from ..db.session import SessionLocal
from ..models.user import User

_bearer = HTTPBearer(auto_error=False)
_tokens: dict[str, datetime] = {}
_user_sessions: dict[str, dict[str, Any]] = {}
_tokens_lock = Lock()

# Default built-in system demo accounts
_DEFAULT_ACCOUNTS = [
    {
        "name": "Nodal Project Officer",
        "email": "officer@gov.in",
        "username": "nodal_officer",
        "password": "officer123",
        "role": "officer",
    },
    {
        "name": "Monitoring Director",
        "email": "monitoring@sameeksha.gov.in",
        "username": "monitoring_dir",
        "password": "monitor123",
        "role": "director",
    },
]


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _ensure_default_accounts_in_db(db: Session) -> None:
    """Ensure baseline demonstration accounts exist in the SQL database."""
    try:
        for acc in _DEFAULT_ACCOUNTS:
            existing = (
                db.query(User)
                .filter(
                    (func.lower(User.email) == acc["email"].lower())
                    | (func.lower(User.username) == acc["username"].lower())
                )
                .first()
            )
            if not existing:
                u = User(
                    name=acc["name"],
                    email=acc["email"].lower(),
                    username=acc["username"].lower(),
                    password_hash=_hash_password(acc["password"]),
                    role=acc["role"],
                )
                db.add(u)
        db.commit()
    except Exception:
        db.rollback()


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


def register_user(
    name: str,
    email: str,
    password: str,
    username: str | None = None,
    db: Session | None = None,
) -> tuple[str, int, dict[str, str]]:
    """Persists a new user directly into the SQL database."""
    clean_email = email.strip().lower()
    clean_name = name.strip()
    clean_username = (username or clean_name.replace(" ", "_").lower()).strip()
    pwd_hash = _hash_password(password)

    session_created = False
    if db is None:
        db = SessionLocal()
        session_created = True

    try:
        # Check if user already exists in database
        existing = (
            db.query(User)
            .filter(
                (func.lower(User.email) == clean_email)
                | (func.lower(User.username) == clean_username)
            )
            .first()
        )
        if existing:
            if existing.password_hash == pwd_hash:
                user_public = {
                    "name": existing.name,
                    "email": existing.email,
                    "username": existing.username,
                    "role": existing.role,
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="An account with this email or username already exists.",
                )
        else:
            # Insert new User row into SQL database
            new_user = User(
                name=clean_name,
                email=clean_email,
                username=clean_username,
                password_hash=pwd_hash,
                role="officer",
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            user_public = {
                "name": new_user.name,
                "email": new_user.email,
                "username": new_user.username,
                "role": new_user.role,
            }

    finally:
        if session_created:
            db.close()

    # Issue session token
    token = secrets.token_urlsafe(32)
    ttl = get_settings().admin_token_ttl_seconds or 86400
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

    with _tokens_lock:
        _tokens[token] = expires_at
        _user_sessions[token] = {"user": user_public, "expires_at": expires_at}
        _cleanup_expired_tokens()

    return token, ttl, user_public


def authenticate_user(
    username_or_email: str,
    password: str,
    db: Session | None = None,
) -> tuple[str, int, dict[str, str]]:
    """Queries user credentials from the database and returns an access token."""
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

    # 2. Query SQL Database
    session_created = False
    if db is None:
        db = SessionLocal()
        session_created = True

    try:
        _ensure_default_accounts_in_db(db)
        clean_id = identifier.lower()
        pwd_hash = _hash_password(password)

        db_user = (
            db.query(User)
            .filter(
                (func.lower(User.email) == clean_id)
                | (func.lower(User.username) == clean_id)
            )
            .first()
        )

        if db_user is not None:
            if db_user.password_hash != pwd_hash:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password.")

            # Record login timestamp in database
            db_user.last_login_at = datetime.now(timezone.utc)
            db.commit()

            user_public = {
                "name": db_user.name,
                "email": db_user.email,
                "username": db_user.username,
                "role": db_user.role,
            }
        else:
            # Fallback auto-registration for official prototype test accounts
            if "@" in identifier and len(password) >= 4:
                fallback_name = identifier.split("@")[0].replace(".", " ").replace("_", " ").title()
                return register_user(
                    name=fallback_name,
                    email=identifier,
                    password=password,
                    db=db,
                )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    finally:
        if session_created:
            db.close()

    # Issue session token
    token = secrets.token_urlsafe(32)
    ttl = settings.admin_token_ttl_seconds or 86400
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

    with _tokens_lock:
        _tokens[token] = expires_at
        _user_sessions[token] = {"user": user_public, "expires_at": expires_at}
        _cleanup_expired_tokens()

    return token, ttl, user_public


def update_user_profile(
    current_user: dict[str, Any],
    name: str,
    username: str | None = None,
    email: str | None = None,
    token: str | None = None,
    db: Session | None = None,
) -> dict[str, str]:
    """Updates user profile details in SQL database and updates active session caches."""
    clean_name = name.strip()
    clean_new_username = username.strip() if username else None
    clean_new_email = email.strip().lower() if email else None

    session_created = False
    if db is None:
        db = SessionLocal()
        session_created = True

    try:
        curr_email = current_user.get("email", "").strip().lower()
        curr_username = current_user.get("username", "").strip().lower()

        db_user = (
            db.query(User)
            .filter(
                (func.lower(User.email) == curr_email)
                | (func.lower(User.username) == curr_username)
            )
            .first()
        )

        if db_user is not None:
            # Check for username conflicts
            if clean_new_username and clean_new_username.lower() != db_user.username.lower():
                conflict = (
                    db.query(User)
                    .filter(
                        func.lower(User.username) == clean_new_username.lower(),
                        User.id != db_user.id,
                    )
                    .first()
                )
                if conflict:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username is already taken by another account.",
                    )
                db_user.username = clean_new_username

            # Check for email conflicts
            if clean_new_email and clean_new_email != db_user.email.lower():
                conflict = (
                    db.query(User)
                    .filter(
                        func.lower(User.email) == clean_new_email,
                        User.id != db_user.id,
                    )
                    .first()
                )
                if conflict:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email is already taken by another account.",
                    )
                db_user.email = clean_new_email

            if clean_name:
                db_user.name = clean_name

            db.commit()
            db.refresh(db_user)

            updated_user = {
                "name": db_user.name,
                "email": db_user.email,
                "username": db_user.username,
                "role": db_user.role,
            }
        else:
            # Fallback update for memory-only/admin profiles
            updated_user = {
                "name": clean_name or current_user.get("name", "Officer"),
                "email": clean_new_email or current_user.get("email", ""),
                "username": clean_new_username or current_user.get("username", "officer"),
                "role": current_user.get("role", "officer"),
            }

        # Update in-memory session cache for this token and any matching active sessions
        with _tokens_lock:
            if token and token in _user_sessions:
                _user_sessions[token]["user"] = updated_user
            for sess in _user_sessions.values():
                u = sess.get("user")
                if u and (
                    (curr_email and u.get("email") == curr_email)
                    or (curr_username and u.get("username") == curr_username)
                ):
                    sess["user"] = updated_user

        return updated_user
    finally:
        if session_created:
            db.close()



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