from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role_name: str = "CONSUMER"  # CONSUMER, BRAND_ADMIN, BRAND_REVIEWER, PLATFORM_ADMIN
    brand_id: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    is_active: bool
    is_superuser: bool
    brand_id: str | None
    roles: list[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user_id: str
    email: str
    roles: list[str]
    brand_id: str | None = None
    user: UserResponse | None = None

