from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.services.auth_service import AuthService


settings = get_settings()

# OAuth2PasswordBearer giúp FastAPI đọc header:
# Authorization: Bearer <access_token>
# tokenUrl dùng để Swagger UI biết endpoint login nằm ở đâu.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login",
)


DbSession = Annotated[Session, Depends(get_db)]
AccessToken = Annotated[str, Depends(oauth2_scheme)]


def get_current_user(
    db: DbSession,
    token: AccessToken,
) -> User:
    """
    Lấy user hiện tại từ JWT access token.

    Quy trình:
    1. Decode token.
    2. Lấy subject trong token, thường là user.id.
    3. Truy vấn database để lấy user mới nhất.

    Lưu ý:
    - Không chỉ tin role trong token.
    - Luôn kiểm tra user trong database để biết tài khoản còn active không.
    """

    try:
        payload = decode_access_token(token)
        token_subject = payload["sub"]
        return AuthService(db).get_current_user_from_token(token_subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(current_user: CurrentUser) -> User:
    """
    Chỉ cho phép admin truy cập endpoint.

    Dùng cho:
    - quản lý user,
    - xem audit log,
    - các thao tác quản trị hệ thống.
    """

    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission is required",
        )

    return current_user


AdminUser = Annotated[User, Depends(require_admin)]


def require_doctor_or_admin(current_user: CurrentUser) -> User:
    """
    Cho phép bác sĩ hoặc admin truy cập endpoint.

    Dùng cho các API nghiệp vụ chính:
    - tạo bệnh nhân,
    - upload MRI,
    - xem lịch sử dự đoán.
    """

    if current_user.role not in {UserRole.doctor, UserRole.admin}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor or admin permission is required",
        )

    return current_user


DoctorOrAdminUser = Annotated[User, Depends(require_doctor_or_admin)]
