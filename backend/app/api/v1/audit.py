from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import require_roles
from backend.app.core.database import get_db
from backend.app.models.audit import AuditLog
from backend.app.models.user import User

router = APIRouter()


class AuditLogResponse(BaseModel):
    id: str
    user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    changes: dict[str, Any]
    ip_address: str | None
    timestamp: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AuditLogResponse])
async def list_audit_logs(
    resource_type: str | None = None,
    action: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN"]))
):
    """
    Query immutable system audit logs for administrative actions,
    reference approvals, and version status changes.
    """
    stmt = select(AuditLog)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    stmt = stmt.order_by(AuditLog.timestamp.desc()).limit(limit)

    result = await db.execute(stmt)
    logs = result.scalars().all()
    return [AuditLogResponse.model_validate(log) for log in logs]
