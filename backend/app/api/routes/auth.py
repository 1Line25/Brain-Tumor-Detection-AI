from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUser, DbSession
from app.core.request import get_client_ip
from app.models.audit_log import AuditAction
from app.schemas.auth import CurrentUserResponse, LoginRequest, LoginResponse
from app.schemas.common import MessageResponse
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService, LoginRateLimitError
from app.services.user_service import UserService


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
    request: Request,
    db: DbSession,
) -> LoginResponse:
    """
    Đăng nhập bằng username/email và password.

    Nếu thành công:
    - trả JWT access token,
    - trả thông tin user để frontend lưu trạng thái đăng nhập.
    """

    client_ip = get_client_ip(request)
    audit_service = AuditService(db)

    try:
        response = AuthService(db).login(data, client_ip=client_ip)
        actor = UserService(db).get_by_id(response.user.id)
        audit_service.log_request(
            request=request,
            action=AuditAction.login,
            actor=actor,
            entity_type="user",
            entity_id=response.user.id,
            metadata={"result": "success"},
        )
        db.commit()
        return response
    except LoginRateLimitError as exc:
        actor = UserService(db).get_by_identifier(data.identifier)
        audit_service.log_request(
            request=request,
            action=AuditAction.login_rate_limited,
            actor=actor,
            entity_type="user" if actor else "authentication",
            entity_id=actor.id if actor else None,
            metadata={
                "result": "rate_limited",
                "retry_after_seconds": exc.retry_after_seconds,
            },
        )
        # Phải commit để lưu bộ đếm thất bại/blocked_until.
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers={
                "Retry-After": str(exc.retry_after_seconds),
            },
        ) from exc
    except ValueError as exc:
        actor = UserService(db).get_by_identifier(data.identifier)
        audit_service.log_request(
            request=request,
            action=AuditAction.login_failed,
            actor=actor,
            entity_type="user" if actor else "authentication",
            entity_id=actor.id if actor else None,
            metadata={"result": "invalid_credentials"},
        )
        # Đăng nhập sai cũng cần commit để giữ bộ đếm rate limit.
        db.commit()
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


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
def logout(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
) -> MessageResponse:
    """
    Ghi nhận người dùng đăng xuất.

    JWT hiện là stateless nên frontend vẫn chịu trách nhiệm xóa token cục bộ.
    """

    AuditService(db).log_request(
        request=request,
        action=AuditAction.logout,
        actor=current_user,
        entity_type="user",
        entity_id=current_user.id,
        metadata={"result": "success"},
    )
    db.commit()
    return MessageResponse(message="Logged out successfully")
