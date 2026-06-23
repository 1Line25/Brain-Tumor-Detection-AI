from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import AdminUser, DbSession
from app.models.audit_log import AuditAction
from app.schemas.audit_log import AuditLogRead
from app.schemas.common import PaginatedResponse, PaginationParams
from app.services.audit_service import AuditService


router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


@router.get(
    "",
    response_model=PaginatedResponse[AuditLogRead],
    status_code=status.HTTP_200_OK,
)
def list_audit_logs(
    db: DbSession,
    _: AdminUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    actor_id: UUID | None = Query(default=None),
    action: AuditAction | None = Query(default=None),
    entity_type: str | None = Query(default=None, max_length=50),
    entity_id: str | None = Query(default=None, max_length=80),
) -> PaginatedResponse[AuditLogRead]:
    """
    Admin xem danh sách audit log có phân trang.

    Có thể lọc theo:
    - actor_id: user thực hiện hành động,
    - action: loại hành động,
    - entity_type/entity_id: đối tượng bị tác động.
    """

    pagination = PaginationParams(page=page, page_size=page_size)

    result = AuditService(db).list_logs(
        pagination=pagination,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
    )

    return PaginatedResponse[AuditLogRead].create(
        items=[AuditLogRead.model_validate(log) for log in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )
