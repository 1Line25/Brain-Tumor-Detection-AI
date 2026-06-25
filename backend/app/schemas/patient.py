from __future__ import annotations

from datetime import date, datetime
import re
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.patient import PatientSex
from app.schemas.user import UserSummary


def normalize_and_validate_phone(value: str | None) -> str | None:
    """Chuẩn hóa số điện thoại về dạng nhất quán để kiểm tra và chống trùng."""

    if value is None:
        return None

    compact = re.sub(r"[\s().-]", "", value.strip())
    if not compact:
        return None

    # Chuẩn hóa số Việt Nam +84 về đầu 0 để 090... và +8490...
    # được nhận diện là cùng một số khi cảnh báo hồ sơ trùng.
    if compact.startswith("+84"):
        compact = f"0{compact[3:]}"

    if compact.startswith("+"):
        digits = compact[1:]
        if (
            not digits.isdigit()
            or not digits.startswith(tuple("123456789"))
            or not 9 <= len(digits) <= 15
        ):
            raise ValueError(
                "Số điện thoại quốc tế phải có dạng +[mã quốc gia][số điện thoại]"
            )
    elif not re.fullmatch(r"0\d{9,10}", compact):
        raise ValueError(
            "Số điện thoại trong nước phải bắt đầu bằng 0 và gồm 10 đến 11 chữ số"
        )

    return compact


class PatientBase(BaseModel):
    """
    Schema nền cho Patient.

    Các schema create/update/read sẽ tái sử dụng field từ đây
    để tránh viết lặp code.
    """

    full_name: str = Field(
        ...,
        min_length=2,
        max_length=120,
        examples=["Tran Van B"],
    )

    date_of_birth: date | None = Field(
        default=None,
        examples=["1998-05-20"],
    )

    sex: PatientSex = Field(
        default=PatientSex.unknown,
        examples=[PatientSex.male],
    )

    phone_number: str | None = Field(
        default=None,
        max_length=20,
        examples=["0901234567"],
    )

    notes: str | None = Field(
        default=None,
        max_length=2000,
        examples=["Bệnh nhân có tiền sử đau đầu kéo dài."],
    )

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        """
        Chuẩn hóa họ tên bệnh nhân.

        Giữ nguyên chữ hoa/thường người dùng nhập,
        chỉ gom khoảng trắng thừa.
        """

        return " ".join(value.strip().split())

    @field_validator("phone_number")
    @classmethod
    def normalize_phone_number(cls, value: str | None) -> str | None:
        """
        Chuẩn hóa số điện thoại nếu có.

        Không validate quá chặt để phù hợp demo/đồ án,
        nhưng vẫn loại bỏ khoảng trắng đầu/cuối.
        """

        return normalize_and_validate_phone(value)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        """
        Chuẩn hóa ghi chú.

        Nếu frontend gửi chuỗi rỗng thì lưu NULL,
        giúp database sạch hơn.
        """

        if value is None:
            return None

        value = value.strip()
        return value or None


class PatientCreate(PatientBase):
    """
    Request tạo hồ sơ bệnh nhân.

    patient_code và created_by không nằm trong request. Database tự sinh mã
    bệnh nhân duy nhất; backend lấy người tạo từ user đang đăng nhập.
    """

    pass


class PatientUpdate(BaseModel):
    """
    Request cập nhật hồ sơ bệnh nhân.

    Tất cả field đều optional để hỗ trợ PATCH.
    """

    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=120,
        examples=["Tran Van C"],
    )

    date_of_birth: date | None = Field(
        default=None,
        examples=["1998-05-20"],
    )

    sex: PatientSex | None = Field(
        default=None,
        examples=[PatientSex.female],
    )

    phone_number: str | None = Field(
        default=None,
        max_length=20,
        examples=["0912345678"],
    )

    notes: str | None = Field(
        default=None,
        max_length=2000,
        examples=["Đã cập nhật thông tin sau lần tái khám."],
    )

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        """
        Chuẩn hóa họ tên nếu field này được gửi lên.
        """

        if value is None:
            return None

        return " ".join(value.strip().split())

    @field_validator("phone_number")
    @classmethod
    def normalize_phone_number(cls, value: str | None) -> str | None:
        """
        Chuẩn hóa số điện thoại nếu field này được gửi lên.
        """

        return normalize_and_validate_phone(value)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        """
        Chuẩn hóa ghi chú nếu field này được gửi lên.
        """

        if value is None:
            return None

        value = value.strip()
        return value or None


class PatientRead(BaseModel):
    """
    Response chi tiết bệnh nhân.

    Dùng cho màn hình xem/cập nhật hồ sơ bệnh nhân.
    """

    id: UUID
    patient_code: str
    full_name: str
    date_of_birth: date | None
    sex: PatientSex
    phone_number: str | None
    notes: str | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {
        # Cho phép Pydantic đọc dữ liệu trực tiếp từ SQLAlchemy model.
        "from_attributes": True,
    }


class PatientDetail(PatientRead):
    """
    Response chi tiết bệnh nhân có kèm thông tin người tạo.

    Dùng khi frontend cần hiển thị:
    "Hồ sơ được tạo bởi bác sĩ/admin nào".
    """

    created_by_user: UserSummary


class PatientSummary(BaseModel):
    """
    Response bệnh nhân rút gọn.

    Dùng trong các response khác, ví dụ prediction history,
    để tránh trả quá nhiều dữ liệu không cần thiết.
    """

    id: UUID
    patient_code: str
    full_name: str
    sex: PatientSex
    date_of_birth: date | None

    model_config = {
        "from_attributes": True,
    }


class PatientDuplicateCheck(BaseModel):
    """Thông tin dùng để tìm hồ sơ có khả năng bị tạo trùng."""

    full_name: str = Field(..., min_length=2, max_length=120)
    date_of_birth: date | None = None
    phone_number: str | None = Field(default=None, max_length=20)
    exclude_patient_id: UUID | None = None

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        return " ".join(value.strip().split())

    @field_validator("phone_number")
    @classmethod
    def normalize_phone_number(cls, value: str | None) -> str | None:
        return normalize_and_validate_phone(value)


class PatientDuplicateResult(BaseModel):
    """Danh sách hồ sơ gần giống để frontend cảnh báo người dùng."""

    possible_duplicates: list[PatientRead] = Field(default_factory=list)
