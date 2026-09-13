from fastapi import APIRouter

from ..core.auth import issue_admin_token
from ..schemas.auth import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    token, expires_in = issue_admin_token(request.username, request.password)
    return LoginResponse(access_token=token, expires_in=expires_in)