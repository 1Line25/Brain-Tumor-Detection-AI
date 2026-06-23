from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.auth import CurrentUserResponse, LoginRequest, LoginResponse
from app.services.auth_service import AuthService


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    data: LoginRequest,
    db: DbSession,
) -> LoginResponse:
    """
    Đăng nhập bằng username/email và password.

    Nếu thành công:
    - trả JWT access token,
    - trả thông tin user để frontend lưu trạng thái đăng nhập.
    """

    try:
        response = AuthService(db).login(data)
        db.commit()
        return response
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_200_OK,
)
def get_me(current_user: CurrentUser) -> CurrentUserResponse:
    """
    Lấy thông tin user đang đăng nhập.

    Frontend dùng endpoint này để kiểm tra token còn hợp lệ
    và biết user hiện tại là admin hay bác sĩ.
    """

    return CurrentUserResponse(user=current_user)
