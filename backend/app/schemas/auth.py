from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role_name: str = "CONSUMER"  # CONSUMER, BRAND_ADMIN, BRAND_REVIEWER, PLATFORM_ADMIN
    brand_id: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    brand_id: Optional[str]
    roles: List[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user_id: str
    email: str
    roles: List[str]
    brand_id: Optional[str] = None
    user: Optional[UserResponse] = None

