from __future__ import annotations

import enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class AuditAction(str, enum.Enum):
    """
    Enum các hành động cần ghi log.

    Việc dùng enum giúp dữ liệu audit nhất quán,
    tránh mỗi nơi ghi một kiểu như: "login", "Login", "user_login".
    """

    login = "login"
    login_failed = "login_failed"
    login_rate_limited = "login_rate_limited"
    logout = "logout"

    create_user = "create_user"
    update_user = "update_user"
    reset_password = "reset_password"
    activate_user = "activate_user"
    deactivate_user = "deactivate_user"

    create_patient = "create_patient"
    view_patient = "view_patient"
    update_patient = "update_patient"

    create_prediction = "create_prediction"
    create_prediction_failed = "create_prediction_failed"
    view_prediction = "view_prediction"
    delete_expired_files = "delete_expired_files"


class AuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Model lưu nhật ký thao tác hệ thống.

    Tối ưu thiết kế:
    - Chỉ lưu thông tin cần truy vết, không lưu dữ liệu ảnh.
    - Dùng JSON metadata để linh hoạt lưu thêm thông tin theo từng loại action.
    - Không bắt buộc actor_id vì có những thao tác do hệ thống tự chạy,
      ví dụ cleanup job xóa ảnh sau 24 giờ.
    """

    __tablename__ = "audit_logs"

    # Người thực hiện hành động.
    # Có thể null nếu action do hệ thống tự chạy, ví dụ worker cleanup file.
    actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="ID người thực hiện hành động, null nếu do hệ thống tự chạy",
    )

    # Loại hành động.
    action: Mapped[AuditAction] = mapped_column(
        Enum(
            AuditAction,
            name="audit_action",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
        index=True,
        comment="Loại hành động được ghi log",
    )

    # Đối tượng bị tác động.
    # Ví dụ:
    # entity_type = "patient", entity_id = id bệnh nhân
    # entity_type = "prediction", entity_id = id lần dự đoán
    entity_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Loại đối tượng bị tác động, ví dụ user/patient/prediction",
    )

    entity_id: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
        index=True,
        comment="ID đối tượng bị tác động, lưu dạng string để linh hoạt",
    )

    # IP và user_agent giúp audit đăng nhập hoặc thao tác nhạy cảm.
    # Có thể null vì không phải thao tác nào cũng đến từ request HTTP.
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="Địa chỉ IP của request, hỗ trợ IPv4/IPv6",
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Thông tin trình duyệt/client thực hiện request",
    )

    # Lưu dữ liệu bổ sung dạng JSON.
    # Ví dụ:
    # {
    #   "patient_code": "BN001",
    #   "predicted_class": "glioma",
    #   "confidence": 0.93
    # }
    #
    # Không nên lưu password, token, hoặc dữ liệu nhạy cảm không cần thiết vào đây.
    metadata_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Thông tin bổ sung cho audit log",
    )

    # Relationship tới User.
    # lazy='raise' giúp tránh tự động query user ngoài ý muốn.
    actor: Mapped["User | None"] = relationship(
        "User",
        back_populates="audit_logs",
        lazy="raise",
    )

    __table_args__ = (
        # Tối ưu màn hình admin xem lịch sử thao tác của một người dùng.
        Index(
            "ix_audit_logs_actor_created_at",
            "actor_id",
            "created_at",
        ),

        # Tối ưu truy vấn lịch sử theo loại hành động.
        # Ví dụ: xem toàn bộ log create_prediction gần đây.
        Index(
            "ix_audit_logs_action_created_at",
            "action",
            "created_at",
        ),

        # Tối ưu truy vết một đối tượng cụ thể.
        # Ví dụ: xem toàn bộ log liên quan đến patient_id X.
        Index(
            "ix_audit_logs_entity",
            "entity_type",
            "entity_id",
        ),
    )
