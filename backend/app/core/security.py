from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings


settings = get_settings()

# Tạo password hasher một lần để tránh khởi tạo lại ở mỗi request.
password_hasher = PasswordHash.recommended()


def get_password_hash(password: str) -> str:
    """
    Hash mật khẩu trước khi lưu vào database.

    Không bao giờ lưu mật khẩu thô của admin/bác sĩ.
    """

    return password_hasher.hash(password)


def hash_password(password: str) -> str:
    """
    Alias giữ tương thích với code cũ.

    Code mới nên dùng get_password_hash().
    """

    return get_password_hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """So sánh mật khẩu đăng nhập với password hash trong database."""

    return password_hasher.verify(plain_password, password_hash)


def create_access_token(
    *,
    subject: str,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Tạo JWT access token.

    subject thường là user.id dạng string. extra_claims dùng để nhúng thêm role
    hoặc metadata nhỏ, nhưng backend vẫn phải kiểm tra quyền từ database.
    """

    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta
        or timedelta(minutes=settings.access_token_expire_minutes)
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expires_at,
        "type": "access",
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Kiểm tra chữ ký, thời hạn và loại JWT.

    ValueError sẽ được router/dependency đổi thành HTTP 401.
    """

    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError as error:
        raise ValueError("Access token is invalid or expired") from error

    if payload.get("type") != "access":
        raise ValueError("Invalid token type")

    if not payload.get("sub"):
        raise ValueError("Token subject is missing")

    return payload
