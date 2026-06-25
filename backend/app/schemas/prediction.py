from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.prediction import (
    PredictionReviewStatus,
    PredictionStatus,
    TumorClass,
)
from app.schemas.patient import PatientSummary
from app.schemas.user import UserSummary


class PredictionBase(BaseModel):
    """
    Schema nền cho Prediction.

    File này chủ yếu dùng response vì upload MRI thường dùng multipart/form-data,
    FastAPI sẽ nhận UploadFile trực tiếp trong router thay vì qua Pydantic schema.
    """

    patient_id: UUID = Field(
        ...,
        description="ID bệnh nhân được chẩn đoán",
    )


class PredictionCreate(PredictionBase):
    """
    Request tạo prediction.

    Lưu ý:
    - Ảnh MRI không nằm trong schema này.
    - Router sẽ nhận ảnh bằng UploadFile.
    - doctor_id không nhận từ frontend, backend lấy từ user đang đăng nhập.
    """

    pass


class PredictionRead(BaseModel):
    """
    Response cơ bản cho một lần dự đoán.

    Dùng cho danh sách lịch sử dự đoán.
    """

    id: UUID
    patient_id: UUID
    doctor_id: UUID

    mri_image_path: str
    gradcam_image_path: str | None

    predicted_class: TumorClass | None
    confidence: float | None
    probabilities: dict[str, float] | None

    status: PredictionStatus
    error_message: str | None

    review_status: PredictionReviewStatus
    clinical_conclusion: str | None
    doctor_notes: str | None
    reviewed_at: datetime | None

    expires_at: datetime
    files_deleted: bool

    created_at: datetime
    updated_at: datetime

    model_config = {
        # Cho phép Pydantic đọc dữ liệu trực tiếp từ SQLAlchemy model.
        "from_attributes": True,
    }


class PredictionDetail(PredictionRead):
    """
    Response chi tiết một lần dự đoán.

    Có kèm thông tin bệnh nhân và bác sĩ để frontend hiển thị đầy đủ.
    """

    patient: PatientSummary
    doctor: UserSummary


class PredictionResult(BaseModel):
    """
    Response trả ngay sau khi upload MRI và chạy model thành công.

    Đây là response quan trọng nhất cho màn hình chẩn đoán.
    """

    prediction_id: UUID = Field(
        ...,
        description="ID của lần dự đoán vừa tạo",
    )

    patient_id: UUID = Field(
        ...,
        description="ID bệnh nhân được chẩn đoán",
    )

    predicted_class: TumorClass = Field(
        ...,
        description="Nhãn model dự đoán",
    )

    confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description="Xác suất cao nhất của predicted_class",
    )

    probabilities: dict[str, float] = Field(
        ...,
        description="Xác suất của toàn bộ lớp phân loại",
    )

    mri_image_path: str = Field(
        ...,
        description="Đường dẫn ảnh MRI gốc",
    )

    gradcam_image_path: str | None = Field(
        default=None,
        description="Đường dẫn ảnh Grad-CAM nếu tạo thành công",
    )

    expires_at: datetime = Field(
        ...,
        description="Thời điểm ảnh MRI và Grad-CAM sẽ bị xóa khỏi storage",
    )

    @field_validator("probabilities")
    @classmethod
    def validate_probabilities(cls, value: dict[str, float]) -> dict[str, float]:
        """
        Validate xác suất từng lớp.

        Tối ưu:
        - Chặn dữ liệu lỗi trước khi trả về frontend.
        - Đảm bảo mọi xác suất đều nằm trong khoảng 0 -> 1.
        """

        for label, probability in value.items():
            if probability < 0 or probability > 1:
                raise ValueError(
                    f"Probability of class '{label}' must be between 0 and 1"
                )

        return value


class PredictionFailed(BaseModel):
    """
    Response khi inference thất bại nhưng backend vẫn ghi lịch sử lỗi.

    Trường hợp này hữu ích khi:
    - Ảnh upload không hợp lệ.
    - Model không load được.
    - Quá trình tạo Grad-CAM bị lỗi.
    """

    prediction_id: UUID | None = Field(
        default=None,
        description="ID prediction nếu đã tạo record lỗi trong database",
    )

    message: str = Field(
        ...,
        examples=["Prediction failed"],
    )

    error_detail: str | None = Field(
        default=None,
        description="Chi tiết lỗi phục vụ debug/demo",
    )


class PredictionReviewUpdate(BaseModel):
    """Nội dung bác sĩ đánh giá một kết quả dự đoán AI."""

    review_status: PredictionReviewStatus = Field(
        default=PredictionReviewStatus.pending,
    )
    clinical_conclusion: str | None = Field(
        default=None,
        max_length=4000,
    )
    doctor_notes: str | None = Field(
        default=None,
        max_length=4000,
    )

    @field_validator("clinical_conclusion", "doctor_notes")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None


class PredictionFilter(BaseModel):
    """
    Bộ lọc lịch sử dự đoán.

    Router có thể dùng schema này để gom query params lại,
    giúp code endpoint sạch hơn.
    """

    patient_id: UUID | None = Field(
        default=None,
        description="Lọc lịch sử theo bệnh nhân",
    )

    doctor_id: UUID | None = Field(
        default=None,
        description="Admin có thể lọc lịch sử theo bác sĩ",
    )

    predicted_class: TumorClass | None = Field(
        default=None,
        description="Lọc theo loại u não được dự đoán",
    )

    status: PredictionStatus | None = Field(
        default=None,
        description="Lọc theo trạng thái dự đoán",
    )

    review_status: PredictionReviewStatus | None = Field(
        default=None,
        description="Lọc theo trạng thái bác sĩ đánh giá kết quả AI",
    )

    patient_keyword: str | None = Field(
        default=None,
        max_length=120,
        description="Tìm theo mã, tên hoặc số điện thoại bệnh nhân",
    )

    doctor_keyword: str | None = Field(
        default=None,
        max_length=120,
        description="Tìm theo username, họ tên hoặc email bác sĩ",
    )

    from_date: datetime | None = Field(
        default=None,
        description="Lọc từ thời điểm tạo",
    )

    to_date: datetime | None = Field(
        default=None,
        description="Lọc đến thời điểm tạo",
    )
