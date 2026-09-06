from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.audit import log_audit_event
from backend.app.core.config import settings
from backend.app.core.security import create_access_token, get_password_hash, verify_password
from backend.app.models.user import Role, User, UserRole
from backend.app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse


class AuthService:
    # Roles that may never be self-assigned via public registration. Granting
    # PLATFORM_ADMIN or BRAND_ADMIN here would let any anonymous visitor mint
    # superuser accounts; these must be provisioned by seeding/CLI only.
    FORBIDDEN_SELF_ASSIGN_ROLES = {"PLATFORM_ADMIN", "BRAND_ADMIN", "BRAND_REVIEWER"}

    @staticmethod
    async def register(db: AsyncSession, data: RegisterRequest) -> UserResponse:
        # Block self-assignment of privileged roles
        if data.role_name.strip().upper() in AuthService.FORBIDDEN_SELF_ASSIGN_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Privileged roles cannot be self-assigned. Contact a platform administrator.",
            )

        # Check existing user
        stmt = select(User).where(User.email == data.email)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists"
            )

        # Retrieve role
        role_stmt = select(Role).where(Role.name == data.role_name.upper())
        role = (await db.execute(role_stmt)).scalar_one_or_none()
        if not role:
            # Create default role if missing
            role = Role(name=data.role_name.upper(), description=f"Default role {data.role_name}")
            db.add(role)
            await db.flush()

        new_user = User(
            email=data.email,
            hashed_password=get_password_hash(data.password),
            full_name=data.full_name,
            is_active=True,
            is_superuser=False  # Privileged roles blocked by FORBIDDEN_SELF_ASSIGN_ROLES
        )
        db.add(new_user)
        await db.flush()

        user_role = UserRole(user_id=new_user.id, role_id=role.id)
        db.add(user_role)

        if data.brand_id:
            from backend.app.models.brand import BrandUser
            b_role = "ADMIN" if data.role_name.upper() == "BRAND_ADMIN" else ("REVIEWER" if data.role_name.upper() == "BRAND_REVIEWER" else "MEMBER")
            b_user = BrandUser(brand_id=data.brand_id, user_id=new_user.id, role=b_role)
            db.add(b_user)

        await db.flush()

        await log_audit_event(
            session=db,
            action="USER_REGISTERED",
            resource_type="USER",
            resource_id=new_user.id,
            user_id=new_user.id,
            changes={"email": new_user.email, "role": role.name}
        )
        await db.commit()

        return UserResponse(
            id=new_user.id,
            email=new_user.email,
            full_name=new_user.full_name,
            is_active=new_user.is_active,
            is_superuser=new_user.is_superuser,
            brand_id=data.brand_id,
            roles=[role.name],
            created_at=new_user.created_at
        )

    @staticmethod
    async def login(db: AsyncSession, credentials: LoginRequest) -> TokenResponse:
        stmt = select(User).where(User.email == credentials.email).options(selectinload(User.roles))
        user = (await db.execute(stmt)).scalar_one_or_none()

        if not user or not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"}
            )

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is disabled")

        # Resolve brand context from BrandUser memberships
        from backend.app.models.brand import BrandUser
        brand_stmt = select(BrandUser.brand_id).where(BrandUser.user_id == user.id)
        primary_brand_id = (await db.execute(brand_stmt)).scalars().first()

        role_names = [r.name for r in user.roles]
        token = create_access_token(
            subject=user.id,
            email=user.email,
            roles=role_names,
            brand_id=primary_brand_id
        )

        await log_audit_event(
            session=db,
            action="USER_LOGIN",
            resource_type="USER",
            resource_id=user.id,
            user_id=user.id
        )
        await db.commit()

        user_resp = UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            brand_id=primary_brand_id,
            roles=role_names,
            created_at=user.created_at
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            user_id=user.id,
            email=user.email,
            roles=role_names,
            brand_id=primary_brand_id,
            user=user_resp
        )

