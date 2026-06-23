from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


# Chỉ import phục vụ type checking.
# Cách này tránh circular import khi ứng dụng chạy.
if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.patient import Patient
    from app.models.prediction import Prediction


class UserRole(str, enum.Enum):
    """Các vai trò được hệ thống hỗ trợ."""

    admin = "admin"
    doctor = "doctor"


class User(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """Tài khoản admin hoặc bác sĩ."""

    __tablename__ = "users"

    __table_args__ = (
        # Hỗ trợ truy vấn danh sách tài khoản theo vai trò và trạng thái.
        # Ví dụ: lấy tất cả tài khoản bác sĩ đang hoạt động.
        Index(
            "ix_users_role_is_active",
            "role",
            "is_active",
        ),

        # Constraint tại database bảo vệ dữ liệu ngay cả khi dữ liệu
        # không được tạo thông qua FastAPI.
        CheckConstraint(
            "char_length(username) >= 3",
            name="username_min_length",
        ),
        CheckConstraint(
            "char_length(full_name) >= 2",
            name="full_name_min_length",
        ),
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(254),
        unique=True,
        nullable=False,
    )

    # Chỉ lưu mật khẩu đã hash bằng Argon2.
    # Không được lưu mật khẩu thuần vào cột này.
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,

            # Lưu "admin" và "doctor" thay vì tên enum.
            values_callable=lambda enum_class: [
                item.value for item in enum_class
            ],

            name="user_role",
            native_enum=True,
        ),

        # Tài khoản mới mặc định là bác sĩ.
        default=UserRole.doctor,
        server_default=UserRole.doctor.value,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,

        # Admin sẽ khóa tài khoản bằng cách đổi thành False
        # thay vì xóa và làm mất lịch sử dự đoán.
        default=True,
        server_default="true",
        nullable=False,
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # lazy="raise" ngăn ORM âm thầm chạy thêm truy vấn khi truy cập
    # relationship. Service phải chủ động dùng selectinload khi cần,
    # giúp tránh lỗi N+1 query và giảm thời gian truy vấn.
    patients: Mapped[list[Patient]] = relationship(
        "Patient",
        back_populates="created_by_user",
        lazy="raise",
    )

    predictions: Mapped[list[Prediction]] = relationship(
        "Prediction",
        back_populates="doctor",
        lazy="raise",
    )

    audit_logs: Mapped[list[AuditLog]] = relationship(
        "AuditLog",
        back_populates="actor",
        lazy="raise",
    )
