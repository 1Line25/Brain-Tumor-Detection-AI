from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserBase(BaseModel):
    """
    Schema nền cho User.

    Các schema create/update/read sẽ kế thừa lại để tránh lặp field.
    """

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        examples=["doctor01"],
    )

    email: EmailStr = Field(
        ...,
        examples=["doctor01@example.com"],
    )

    full_name: str = Field(
        ...,
        min_length=2,
        max_length=120,
        examples=["Nguyen Van A"],
    )

    role: UserRole = Field(
        default=UserRole.doctor,
        examples=[UserRole.doctor],
    )

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        """
        Chuẩn hóa username.

        Tối ưu:
        - Strip khoảng trắng đầu/cuối.
        - Chuyển lowercase để tránh trùng kiểu Doctor01 và doctor01.
        """

        return value.strip().lower()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        """
        Chuẩn hóa email.

        EmailStr đã validate định dạng email,
        ở đây chỉ đưa về lowercase để so sánh nhất quán.
        """

        return str(value).strip().lower()

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        """
        Chuẩn hóa họ tên.

        Không lowercase tên người vì sẽ làm mất định dạng hiển thị.
        """

        return " ".join(value.strip().split())


class UserCreate(UserBase):
    """
    Request tạo user mới.

    Thường chỉ admin được phép gọi API này.
    """

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        examples=["StrongPassword123"],
    )


class UserUpdate(BaseModel):
    """
    Request cập nhật user.

    Tất cả field đều optional để hỗ trợ PATCH:
    frontend gửi field nào thì backend cập nhật field đó.
    """

    email: EmailStr | None = Field(
        default=None,
        examples=["new_email@example.com"],
    )

    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=120,
        examples=["Nguyen Van B"],
    )

    role: UserRole | None = Field(
        default=None,
        examples=[UserRole.doctor],
    )

    is_active: bool | None = Field(
        default=None,
        description="Admin dùng field này để khóa/mở khóa tài khoản",
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        """
        Chuẩn hóa email nếu field này được gửi lên.
        """

        if value is None:
            return None

        return str(value).strip().lower()

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        """
        Chuẩn hóa họ tên nếu field này được gửi lên.
        """

        if value is None:
            return None

        return " ".join(value.strip().split())


class PasswordChange(BaseModel):
    """
    Request đổi mật khẩu cho user đang đăng nhập.

    Backend sẽ kiểm tra old_password đúng trước khi đổi sang new_password.
    """

    old_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        examples=["OldPassword123"],
    )

    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        examples=["NewPassword123"],
    )


class PasswordResetByAdmin(BaseModel):
    """
    Request admin đặt lại mật khẩu cho user khác.

    Không cần old_password vì admin có quyền quản trị.
    """

    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        examples=["NewPassword123"],
    )


class UserRead(BaseModel):
    """
    Response trả thông tin user cho frontend.

    Không bao giờ trả password_hash ra ngoài API.
    """

    id: UUID
    username: str
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        # Cho phép Pydantic đọc dữ liệu trực tiếp từ SQLAlchemy model.
        "from_attributes": True,
    }


class UserSummary(BaseModel):
    """
    Response user rút gọn.

    Dùng khi chỉ cần hiển thị thông tin ngắn,
    ví dụ trong chi tiết prediction: bác sĩ thực hiện là ai.
    """

    id: UUID
    username: str
    full_name: str
    role: UserRole

    model_config = {
        "from_attributes": True,
    }
