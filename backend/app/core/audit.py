from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit import AuditLog


async def log_audit_event(
    session: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    user_id: str | None = None,
    changes: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """
    Records an immutable audit event in the database.
    """
    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes or {},
        ip_address=ip_address,
    )
    session.add(log_entry)
    await session.flush()
    return log_entry
