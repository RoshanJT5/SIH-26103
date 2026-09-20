from typing import Any
from urllib.parse import quote
from fastapi import APIRouter, Depends, Query

from ..core.auth import (
    authenticate_user,
    get_current_user,
    get_optional_current_user,
    register_user,
)
from ..schemas.auth import (
    LoginRequest,
    LoginResponse,
    RouteVerificationRequest,
    RouteVerificationResponse,
    SignupRequest,
    UserProfileResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])

PUBLIC_FRONTEND_PAGES = [
    "/",
    "/help",
    "/faq",
    "/documents",
    "/updates",
    "/updates/:id",
    "/login",
    "/signup",
]

PROTECTED_FRONTEND_PAGES = [
    "/dashboard",
    "/monitoring",
    "/monitoring/changes",
    "/early-warnings",
    "/interventions",
    "/risk/trends",
    "/simulation",
    "/projects",
    "/projects/:id",
    "/analytics",
    "/analytics/models",
]


def is_path_protected(path: str) -> bool:
    clean = (path or "/").strip().split("?")[0].rstrip("/")
    if not clean:
        clean = "/"

    # Explicit public prefixes and exact matches
    public_exact = {"/", "/help", "/faq", "/documents", "/login", "/signup"}
    if clean in public_exact or clean.startswith("/updates"):
        return False

    # Check protected paths
    for p in PROTECTED_FRONTEND_PAGES:
        base = p.split("/:")[0].rstrip("/")
        if clean == base or clean.startswith(base + "/"):
            return True

    # Default: non-public paths are protected
    return True


@router.post("/signup", response_model=LoginResponse)
def signup(request: SignupRequest) -> LoginResponse:
    token, expires_in, user_dict = register_user(
        name=request.name,
        email=request.email,
        password=request.password,
        username=request.username,
    )
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserProfileResponse(**user_dict),
    )


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    token, expires_in, user_dict = authenticate_user(
        username_or_email=request.username,
        password=request.password,
    )
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserProfileResponse(**user_dict),
    )


@router.get("/me", response_model=UserProfileResponse)
def get_authenticated_profile(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> UserProfileResponse:
    return UserProfileResponse(
        name=current_user.get("name", "Officer"),
        email=current_user.get("email", ""),
        username=current_user.get("username", "officer"),
        role=current_user.get("role", "officer"),
    )


@router.get("/check-protected")
def check_protected_access(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    return {
        "authenticated": True,
        "user": current_user,
        "message": f"Welcome {current_user.get('name')}. You have full access to protected dashboard and monitoring routes.",
    }


@router.get("/verify-route", response_model=RouteVerificationResponse)
def verify_route_get(
    route: str = Query(..., description="Target frontend route path to check"),
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> RouteVerificationResponse:
    return _build_route_verification_response(route, current_user)


@router.post("/verify-route", response_model=RouteVerificationResponse)
def verify_route_post(
    request: RouteVerificationRequest,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> RouteVerificationResponse:
    return _build_route_verification_response(request.route, current_user)


def _build_route_verification_response(
    route: str,
    current_user: dict[str, Any] | None,
) -> RouteVerificationResponse:
    protected = is_path_protected(route)
    if not protected:
        return RouteVerificationResponse(
            route=route,
            is_protected=False,
            allowed=True,
            destination=route,
            redirect_url=None,
            reason=None,
            user=UserProfileResponse(**current_user) if current_user else None,
        )

    if current_user is not None:
        return RouteVerificationResponse(
            route=route,
            is_protected=True,
            allowed=True,
            destination=route,
            redirect_url=None,
            reason=None,
            user=UserProfileResponse(
                name=current_user.get("name", "Officer"),
                email=current_user.get("email", ""),
                username=current_user.get("username", "officer"),
                role=current_user.get("role", "officer"),
            ),
        )

    # Protected and unauthenticated -> redirect to /login
    redirect_target = quote(route)
    redirect_url = f"/login?redirect={redirect_target}&reason=auth_required"
    return RouteVerificationResponse(
        route=route,
        is_protected=True,
        allowed=False,
        destination=None,
        redirect_url=redirect_url,
        reason="Authentication required. Please login or signup.",
        user=None,
    )


@router.get("/dashboard-entry")
def dashboard_entry(
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> dict[str, Any]:
    """Entrypoint that routes authenticated users to dashboard and unauthenticated visitors to login."""
    if current_user:
        return {
            "destination": "/dashboard",
            "allowed": True,
            "user": current_user,
            "message": f"Welcome back, {current_user.get('name')}.",
        }
    return {
        "destination": "/login?redirect=%2Fdashboard&reason=auth_required",
        "allowed": False,
        "message": "Authentication required. Please login or signup.",
    }


@router.get("/routes")
def get_route_access_policy() -> dict[str, Any]:
    """Provides a clear map of public vs protected routes and redirection policy across the platform."""
    return {
        "redirection_policy": {
            "unauthenticated_redirect_target": "/login",
            "redirect_parameter": "redirect",
            "default_authenticated_destination": "/dashboard",
            "auth_required_reason": "auth_required",
        },
        "public": {
            "description": "Accessible to all visitors without login or signup",
            "frontend_pages": PUBLIC_FRONTEND_PAGES,
            "backend_endpoints": [
                "GET /",
                "GET /help",
                "GET /faq",
                "GET /documents",
                "GET /updates",
                "GET /login",
                "GET /signup",
                "GET /api/health",
                "POST /api/auth/login",
                "POST /api/auth/signup",
                "GET /api/auth/routes",
                "GET /api/auth/verify-route",
                "POST /api/auth/verify-route",
                "GET /api/auth/dashboard-entry",
                "GET /api/updates",
            ],
        },
        "protected": {
            "description": "Requires authentication (login or signup required). Unauthenticated requests redirect to /login.",
            "frontend_pages": PROTECTED_FRONTEND_PAGES,
            "backend_endpoints": [
                "GET /dashboard",
                "GET /monitoring",
                "GET /projects",
                "GET /analytics",
                "GET /simulation",
                "GET /api/auth/me",
                "GET /api/auth/check-protected",
                "POST /api/projects/upload (admin only)",
            ],
        },
    }