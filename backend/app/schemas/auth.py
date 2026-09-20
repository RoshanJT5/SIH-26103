from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    email: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=4, max_length=256)
    username: str | None = Field(default=None, max_length=128)


class UserProfileResponse(BaseModel):
    name: str
    email: str
    username: str
    role: str = "officer"


class UpdateProfileRequest(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    username: str | None = Field(default=None, max_length=128)
    email: str | None = Field(default=None, max_length=128)



class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfileResponse | None = None


class RouteVerificationRequest(BaseModel):
    route: str = Field(min_length=1, max_length=256)


class RouteVerificationResponse(BaseModel):
    route: str
    is_protected: bool
    allowed: bool
    destination: str | None = None
    redirect_url: str | None = None
    reason: str | None = None
    user: UserProfileResponse | None = None