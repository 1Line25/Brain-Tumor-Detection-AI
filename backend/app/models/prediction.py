from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, Float, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.patient import Patient
    from app.models.user import User


class TumorClass(str, enum.Enum):
    """
    Enum các lớp phân loại u não.

    Lưu ý:
    - Các giá trị này phải khớp với thứ tự label khi train model.
    - Nếu model của bạn dùng tên lớp khác, chỉ cần sửa enum này và config MODEL_LABELS.
    """

    glioma_tumor = "glioma_tumor"
    meningioma_tumor = "meningioma_tumor"
    no_tumor = "no_tumor"
    pituitary_tumor = "pituitary_tumor"


class PredictionStatus(str, enum.Enum):
    """
    Trạng thái của một lần dự đoán.

    Dùng status để backend dễ quản lý nếu inference lỗi,
    hoặc nếu sau này bạn muốn thêm hàng đợi xử lý ảnh.
    """

    success = "success"
    failed = "failed"


class Prediction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Model lưu lịch sử dự đoán MRI.

    Tối ưu thiết kế:
    - Chỉ lưu đường dẫn file trong database, không lưu ảnh nhị phân vào DB.
      Cách này nhẹ hơn, dễ backup DB hơn và phù hợp với storage folder.
    - Lưu probabilities dạng JSON để linh hoạt theo số lớp model.
    - Có expires_at để worker/job tự xóa ảnh MRI và Grad-CAM sau 24 giờ.
    """

    __tablename__ = "predictions"

    # Bệnh nhân được chẩn đoán.
    # ondelete='RESTRICT' để tránh mất lịch sử nếu ai đó cố xóa bệnh nhân.
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="ID bệnh nhân liên quan đến lần dự đoán",
    )

    # Người thực hiện dự đoán, thường là bác sĩ đang đăng nhập.
    # ondelete='RESTRICT' để giữ tính truy vết lịch sử y tế.
    doctor_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="ID bác sĩ thực hiện dự đoán",
    )

    # Đường dẫn tương đối tới ảnh MRI trong storage.
    # Ví dụ: storage/mri/2026/06/23/uuid.png
    # Không lưu absolute path để Docker/deploy dễ đổi thư mục gốc.
    mri_image_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Đường dẫn tương đối tới ảnh MRI đã upload",
    )

    # Đường dẫn tương đối tới ảnh Grad-CAM.
    # Có thể null nếu inference lỗi hoặc chưa tạo Grad-CAM.
    gradcam_image_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Đường dẫn tương đối tới ảnh Grad-CAM",
    )

    # Nhãn model dự đoán có xác suất cao nhất.
    predicted_class: Mapped[TumorClass | None] = mapped_column(
        Enum(
            TumorClass,
            name="tumor_class",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=True,
        comment="Lớp u não được model dự đoán",
    )

    # Xác suất cao nhất tương ứng với predicted_class.
    # Dùng Float vì đây là giá trị 0.0 -> 1.0.
    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Độ tin cậy cao nhất của kết quả dự đoán",
    )

    # Lưu toàn bộ xác suất từng lớp.
    # Ví dụ:
    # {
    #   "glioma": 0.12,
    #   "meningioma": 0.08,
    #   "pituitary": 0.77,
    #   "no_tumor": 0.03
    # }
    # JSON giúp dễ mở rộng nếu model sau này có thêm lớp.
    probabilities: Mapped[dict[str, float] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Xác suất dự đoán của tất cả các lớp",
    )

    # Trạng thái dự đoán.
    # Nếu lỗi đọc ảnh/model thì status='failed' và error_message sẽ có nội dung.
    status: Mapped[PredictionStatus] = mapped_column(
        Enum(
            PredictionStatus,
            name="prediction_status",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
        default=PredictionStatus.success,
        server_default=PredictionStatus.success.value,
        index=True,
        comment="Trạng thái xử lý dự đoán",
    )

    # Lưu lỗi inference nếu có.
    # Không trả toàn bộ lỗi kỹ thuật cho frontend trong production,
    # nhưng lưu ở DB giúp debug khi làm đồ án/demo.
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Thông tin lỗi nếu dự đoán thất bại",
    )

    # Thời điểm file MRI và Grad-CAM hết hạn.
    # Worker sẽ dựa vào field này để xóa file sau 24 giờ.
    # Lưu ý: xóa file vật lý, còn record lịch sử vẫn giữ lại.
    expires_at: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
        comment="Thời điểm ảnh MRI/Grad-CAM cần được xóa khỏi storage",
    )

    # Đánh dấu đã xóa file vật lý hay chưa.
    # Field này giúp cleanup job không cố xóa đi xóa lại cùng một file.
    files_deleted: Mapped[bool] = mapped_column(
        default=False,
        server_default="false",
        nullable=False,
        index=True,
        comment="Đánh dấu ảnh MRI và Grad-CAM đã bị xóa khỏi storage chưa",
    )

    # Relationship tới Patient.
    # lazy='raise' giúp tránh query phụ phát sinh ngoài ý muốn.
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="predictions",
        lazy="raise",
    )

    # Relationship tới User/bác sĩ.
    doctor: Mapped["User"] = relationship(
        "User",
        back_populates="predictions",
        lazy="raise",
    )

    __table_args__ = (
        # Đảm bảo confidence luôn nằm trong khoảng xác suất hợp lệ.
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="confidence_range",
        ),

        # Nếu status là failed thì nên có error_message để dễ debug.
        CheckConstraint(
            "status != 'failed' OR error_message IS NOT NULL",
            name="failed_has_error",
        ),

        # Tối ưu truy vấn lịch sử dự đoán của một bệnh nhân theo thời gian.
        Index(
            "ix_predictions_patient_created_at",
            "patient_id",
            "created_at",
        ),

        # Tối ưu truy vấn lịch sử dự đoán của một bác sĩ theo thời gian.
        Index(
            "ix_predictions_doctor_created_at",
            "doctor_id",
            "created_at",
        ),

        # Tối ưu cleanup job:
        # tìm các record đã hết hạn nhưng chưa xóa file.
        Index(
            "ix_predictions_cleanup",
            "files_deleted",
            "expires_at",
        ),
    )
