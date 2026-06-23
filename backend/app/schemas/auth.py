from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    """
    Request đăng nhập.

    Cho phép dùng username hoặc email ở cùng một field `identifier`,
    giúp frontend đơn giản hơn.
    """

    identifier: str = Field(
        ...,
        min_length=3,
        max_length=120,
        examples=["doctor01"],
        description="Username hoặc email",
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        examples=["StrongPassword123"],
    )


class TokenResponse(BaseModel):
    """
    Response trả JWT access token sau khi đăng nhập thành công.

    access_token sẽ được frontend lưu tạm, ví dụ localStorage/sessionStorage.
    Khi gọi API cần gửi header:
    Authorization: Bearer <access_token>
    """

    access_token: str = Field(
        ...,
        description="JWT access token",
    )

    token_type: str = Field(
        default="bearer",
        examples=["bearer"],
    )


class CurrentUserResponse(BaseModel):
    """
    Response trả thông tin user đang đăng nhập.

    Dùng cho API /auth/me để frontend biết:
    - Ai đang đăng nhập
    - Role là admin hay doctor
    - Có còn active không
    """

    user: UserRead


class LoginResponse(TokenResponse):
    """
    Response đăng nhập hoàn chỉnh.

    Trả cả token và thông tin user để frontend không cần gọi thêm /auth/me
    ngay sau khi login.
    """

    user: UserRead