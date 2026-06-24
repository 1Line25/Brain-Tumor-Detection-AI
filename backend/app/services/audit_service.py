from __future__ import annotations

from uuid import UUID

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.request import get_client_ip, get_user_agent
from app.models.audit_log import AuditAction, AuditLog
from app.models.user import User
from app.schemas.common import PaginatedResponse, PaginationParams


class AuditService:
    """
    Service ghi và truy vấn audit log.

    Tối ưu thiết kế:
    - Gom logic ghi log vào một nơi.
    - Cho phép actor_id = None với các job hệ thống, ví dụ cleanup file.
    - Metadata linh hoạt dạng JSON nhưng vẫn tránh lưu thông tin nhạy cảm.
    """

    def __init__(self, db: Session):
        """
        db là database session được FastAPI inject từ dependency get_db().
        """

        self.db = db

    def log(
        self,
        *,
        action: AuditAction,
        actor: User | None = None,
        entity_type: str | None = None,
        entity_id: UUID | str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        """
        Ghi một audit log mới.

        Lưu ý:
        - Không commit trực tiếp tại đây.
        - Router/service gọi bên ngoài sẽ commit cùng nghiệp vụ chính.
        - Cách này giúp nếu nghiệp vụ lỗi thì audit log cũng rollback theo.
        """

        audit_log = AuditLog(
            actor_id=actor.id if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_json=self._sanitize_metadata(metadata),
        )

        self.db.add(audit_log)
        self.db.flush()

        return audit_log

    def log_request(
        self,
        *,
        request: Request,
        action: AuditAction,
        actor: User | None = None,
        entity_type: str | None = None,
        entity_id: UUID | str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        """Ghi audit log và tự lấy IP/user-agent từ HTTP request."""

        return self.log(
            action=action,
            actor=actor,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            metadata=metadata,
        )

    def list_logs(
        self,
        *,
        pagination: PaginationParams,
        actor_id: UUID | None = None,
        action: AuditAction | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
    ) -> PaginatedResponse[AuditLog]:
        """
        Lấy danh sách audit log có phân trang.

        Thường chỉ admin được phép xem API này.
        """

        filters = []

        if actor_id is not None:
            filters.append(AuditLog.actor_id == actor_id)

        if action is not None:
            filters.append(AuditLog.action == action)

        if entity_type is not None:
            filters.append(AuditLog.entity_type == entity_type)

        if entity_id is not None:
            filters.append(AuditLog.entity_id == str(entity_id))

        total_statement = select(func.count()).select_from(AuditLog)

        list_statement = (
            select(AuditLog)
            .options(joinedload(AuditLog.actor))
            .order_by(AuditLog.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )

        if filters:
            total_statement = total_statement.where(*filters)
            list_statement = list_statement.where(*filters)

        total = self.db.scalar(total_statement) or 0
        items = list(self.db.scalars(list_statement).all())

        return PaginatedResponse[AuditLog].create(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    def _sanitize_metadata(self, metadata: dict | None) -> dict | None:
        """
        Loại bỏ các key nhạy cảm khỏi metadata trước khi lưu.

        Tối ưu bảo mật:
        - Tránh vô tình lưu password/token vào database.
        - Audit log thường tồn tại lâu, nên không nên chứa dữ liệu bí mật.
        """

        if metadata is None:
            return None

        blocked_keys = {
            "password",
            "old_password",
            "new_password",
            "password_hash",
            "token",
            "access_token",
            "refresh_token",
            "authorization",
        }

        sanitized = {}

        for key, value in metadata.items():
            normalized_key = key.lower()

            if normalized_key in blocked_keys:
                sanitized[key] = "***"
            else:
                sanitized[key] = value

        return sanitized
