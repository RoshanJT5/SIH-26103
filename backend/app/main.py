from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .api.auth import router as auth_router
from .api.assistant import router as assistant_router
from .api.datasets import router as datasets_router
from .api.health import router as health_router
from .api.projects import router as projects_router
from .api.monitoring import router as monitoring_router
from .api.trends import router as trends_router
from .api.interventions import router as interventions_router
from .api.early_warnings import router as early_warnings_router
from .api.project_extensions import router as project_ext_router
from .api.analytics_extra import router as analytics_extra_router
from .api.updates import router as updates_router
from .core.config import get_settings
from .core.auth import _tokens, _tokens_lock, _user_sessions
from .db.session import engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Ensure database connection and initialize tables if not present
    with engine.connect():
        pass
    from .db.base import Base
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
parsed_origins = [
    origin.strip().rstrip("/")
    for origin in settings.allowed_origins.split(",")
    if origin.strip()
]
is_wildcard = "*" in parsed_origins

if is_wildcard:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=parsed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(assistant_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(datasets_router, prefix="/api")
app.include_router(monitoring_router, prefix="/api")
app.include_router(trends_router, prefix="/api")
app.include_router(interventions_router, prefix="/api")
app.include_router(early_warnings_router, prefix="/api")
app.include_router(project_ext_router, prefix="/api")
app.include_router(analytics_extra_router, prefix="/api")
app.include_router(updates_router, prefix="/api")


def _get_user_from_request(request: Request) -> dict[str, Any] | None:
    auth_header = request.headers.get("Authorization")
    token: str | None = None
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")
    elif "token" in request.query_params:
        token = request.query_params.get("token")

    if not token:
        return None

    now = datetime.now(timezone.utc)
    with _tokens_lock:
        session = _user_sessions.get(token)
        if session and session["expires_at"] > now:
            return session["user"]
        exp = _tokens.get(token)
        if exp and exp > now:
            return {
                "name": "System Administrator",
                "email": "admin@gov.in",
                "username": settings.admin_username or "admin",
                "role": "admin",
            }
    return None


def _handle_protected_page(request: Request, path: str):
    user = _get_user_from_request(request)
    if user is not None:
        return {
            "page": path,
            "access": "granted",
            "authenticated": True,
            "user": user,
            "message": f"Access granted to {path}.",
        }

    target_query = quote(path)
    return RedirectResponse(
        url=f"/login?redirect={target_query}&reason=auth_required",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


# Public Web Pages (Accessible without authentication)
@app.get("/", include_in_schema=False)
def root() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "access": "public",
        "pages": {
            "public": ["/", "/help", "/faq", "/documents", "/updates", "/login", "/signup"],
            "protected": [
                "/dashboard",
                "/monitoring",
                "/early-warnings",
                "/interventions",
                "/risk/trends",
                "/simulation",
                "/projects",
                "/analytics",
            ],
        },
        "health": "/api/health",
        "docs": "/docs",
    }


@app.get("/faq", include_in_schema=False)
def public_faq():
    return {
        "page": "/faq",
        "access": "public",
        "title": "Frequently Asked Questions",
        "description": "Public knowledge base and portal guidance accessible without login.",
    }


@app.get("/help", include_in_schema=False)
def public_help():
    return {
        "page": "/help",
        "access": "public",
        "title": "Help and Support",
        "description": "Public documentation, accessibility guidance, and grievance contacts.",
    }


@app.get("/documents", include_in_schema=False)
def public_documents():
    return {
        "page": "/documents",
        "access": "public",
        "title": "Public Documents Repository",
        "description": "Open reports, standards, and guidelines accessible without authentication.",
    }


@app.get("/login", include_in_schema=False)
def public_login(redirect: str = "/dashboard"):
    return {
        "page": "/login",
        "access": "public",
        "title": "Officer Login Gateway",
        "redirect_target": redirect,
    }


@app.get("/signup", include_in_schema=False)
def public_signup(redirect: str = "/dashboard"):
    return {
        "page": "/signup",
        "access": "public",
        "title": "Officer Registration Gateway",
        "redirect_target": redirect,
    }


# Protected Web Pages (Redirect to /login if unauthenticated)
@app.get("/dashboard", include_in_schema=False)
def protected_dashboard(request: Request):
    return _handle_protected_page(request, "/dashboard")


@app.get("/monitoring", include_in_schema=False)
def protected_monitoring(request: Request):
    return _handle_protected_page(request, "/monitoring")


@app.get("/monitoring/{subpath:path}", include_in_schema=False)
def protected_monitoring_sub(request: Request, subpath: str):
    return _handle_protected_page(request, f"/monitoring/{subpath}")


@app.get("/early-warnings", include_in_schema=False)
def protected_early_warnings(request: Request):
    return _handle_protected_page(request, "/early-warnings")


@app.get("/interventions", include_in_schema=False)
def protected_interventions(request: Request):
    return _handle_protected_page(request, "/interventions")


@app.get("/risk/trends", include_in_schema=False)
def protected_risk_trends(request: Request):
    return _handle_protected_page(request, "/risk/trends")


@app.get("/simulation", include_in_schema=False)
def protected_simulation(request: Request):
    return _handle_protected_page(request, "/simulation")


@app.get("/projects", include_in_schema=False)
def protected_projects(request: Request):
    return _handle_protected_page(request, "/projects")


@app.get("/projects/{subpath:path}", include_in_schema=False)
def protected_projects_sub(request: Request, subpath: str):
    return _handle_protected_page(request, f"/projects/{subpath}")


@app.get("/analytics", include_in_schema=False)
def protected_analytics(request: Request):
    return _handle_protected_page(request, "/analytics")


@app.get("/analytics/{subpath:path}", include_in_schema=False)
def protected_analytics_sub(request: Request, subpath: str):
    return _handle_protected_page(request, f"/analytics/{subpath}")
