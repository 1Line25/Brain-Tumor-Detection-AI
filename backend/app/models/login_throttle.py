from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class LoginThrottle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Trạng thái giới hạn đăng nhập theo tài khoản hoặc địa chỉ IP."""

    __tablename__ = "login_throttles"

    scope_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    scope_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    failed_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    blocked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "scope_type",
            "scope_key",
            name="uq_login_throttles_scope",
        ),
        Index(
            "ix_login_throttles_blocked_until",
            "blocked_until",
        ),
    )
