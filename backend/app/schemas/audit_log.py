from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.audit_log import AuditAction
from app.schemas.user import UserSummary


class AuditLogRead(BaseModel):
    """
    Response trả thông tin một audit log.

    Dùng cho màn hình admin xem lịch sử thao tác hệ thống.
    """

    id: UUID
    actor_id: UUID | None
    actor: UserSummary | None
    action: AuditAction
    entity_type: str | None
    entity_id: str | None
    ip_address: str | None
    user_agent: str | None
    metadata_json: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class AuditLogFilter(BaseModel):
    """
    Bộ lọc audit log.

    Router có thể dùng schema này để gom query params lại,
    giúp code endpoint gọn và dễ mở rộng.
    """

    actor_id: UUID | None = Field(default=None)
    action: AuditAction | None = Field(default=None)
    entity_type: str | None = Field(default=None, max_length=50)
    entity_id: str | None = Field(default=None, max_length=80)
