import uuid
from datetime import datetime

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """
    Thêm UUID primary key cho model.

    UUID không làm lộ số lượng bản ghi như ID tăng dần và có thể
    được tạo trước khi dữ liệu được ghi vào PostgreSQL.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,

        # Tạo UUID tại application để có thể dùng ID cho tên file MRI
        # trước khi transaction được commit.
        default=uuid.uuid4,
    )


class TimestampMixin:
    """Thêm thời gian tạo và cập nhật cho model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),

        # PostgreSQL tự tạo thời gian nhằm tránh phụ thuộc múi giờ
        # hoặc đồng hồ của máy chạy backend.
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),

        # SQLAlchemy cập nhật giá trị khi object được chỉnh sửa
        # thông qua ORM.
        onupdate=func.now(),
        nullable=False,
    )