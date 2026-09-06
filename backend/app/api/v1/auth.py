from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from backend.app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Registers a new user (Consumer, Brand Admin, or Reviewer).
    """
    return await AuthService.register(db, data)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticates user and issues JWT Bearer token with RBAC roles.
    """
    return await AuthService.login(db, credentials)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Returns authenticated user's profile and assigned roles.
    """
    primary_brand_id = current_user.brand_memberships[0].brand_id if current_user.brand_memberships else None
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        brand_id=primary_brand_id,
        roles=[r.name for r in current_user.roles],
        created_at=current_user.created_at
    )
