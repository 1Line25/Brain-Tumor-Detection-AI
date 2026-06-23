from __future__ import annotations

import enum
from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.prediction import Prediction
    from app.models.user import User


class PatientSex(str, enum.Enum):
    """
    Enum giới tính bệnh nhân.

    Dùng enum thay vì String tự do để tránh dữ liệu bị nhập lung tung:
    ví dụ: "nam", "Nam", "male", "M" bị lẫn lộn.
    """

    male = "male"
    female = "female"
    other = "other"
    unknown = "unknown"


class Patient(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Model lưu thông tin bệnh nhân.

    Tối ưu thiết kế:
    - Tách bệnh nhân ra khỏi bảng prediction để tránh lặp thông tin bệnh nhân
      ở mỗi lần chẩn đoán.
    - Dùng patient_code để tìm kiếm nhanh thay vì phụ thuộc vào tên.
    - Không xóa cascade từ patient sang prediction để tránh mất lịch sử y tế.
    """

    __tablename__ = "patients"

    # Mã bệnh nhân nội bộ của hệ thống.
    # Có unique để tránh tạo trùng hồ sơ.
    patient_code: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        nullable=False,
        index=True,
        comment="Mã bệnh nhân duy nhất trong hệ thống",
    )

    # Họ tên bệnh nhân.
    # Không dùng index mặc định cho full_name vì tìm kiếm tên thường cần LIKE/ILIKE,
    # sau này có thể tối ưu bằng PostgreSQL trigram nếu cần.
    full_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        comment="Họ tên bệnh nhân",
    )

    # Ngày sinh có thể để trống vì trong thực tế/demo có thể chưa đủ dữ liệu.
    date_of_birth: Mapped[date | None] = mapped_column(
        nullable=True,
        comment="Ngày sinh bệnh nhân",
    )

    # Giới tính dùng Enum để dữ liệu nhất quán.
    sex: Mapped[PatientSex] = mapped_column(
        Enum(
            PatientSex,
            name="patient_sex",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
        default=PatientSex.unknown,
        server_default=PatientSex.unknown.value,
        comment="Giới tính bệnh nhân",
    )

    # Số điện thoại là optional.
    # Không đặt unique vì một số bệnh nhân có thể dùng chung số người thân.
    phone_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Số điện thoại liên hệ",
    )

    # Ghi chú y tế hoặc ghi chú nội bộ.
    # Text phù hợp hơn String vì ghi chú có thể dài.
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Ghi chú thêm về bệnh nhân",
    )

    # Bác sĩ/admin tạo hồ sơ bệnh nhân.
    # ondelete='RESTRICT' để không cho xóa user nếu user đó đang gắn với hồ sơ y tế.
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="ID người tạo hồ sơ bệnh nhân",
    )

    # Relationship tới User.
    # lazy='raise' giúp phát hiện lỗi N+1 query sớm:
    # nếu muốn lấy user kèm patient thì phải chủ động eager load ở query.
    created_by_user: Mapped["User"] = relationship(
        "User",
        back_populates="patients",
        lazy="raise",
    )

    # Một bệnh nhân có thể có nhiều lần dự đoán/chẩn đoán.
    # Không cascade delete để tránh vô tình xóa lịch sử chẩn đoán.
    predictions: Mapped[list["Prediction"]] = relationship(
        "Prediction",
        back_populates="patient",
        lazy="raise",
    )

    __table_args__ = (
        # Ràng buộc độ dài tối thiểu giúp tránh dữ liệu rác như "", "A".
        CheckConstraint(
            "char_length(patient_code) >= 3",
            name="patient_code_min_length",
        ),
        CheckConstraint(
            "char_length(full_name) >= 2",
            name="full_name_min_length",
        ),

        # Tối ưu truy vấn danh sách bệnh nhân theo bác sĩ và thời gian tạo.
        # Ví dụ: bác sĩ xem các bệnh nhân mình đã tạo gần đây.
        Index(
            "ix_patients_created_by_created_at",
            "created_by",
            "created_at",
        ),
    )   
