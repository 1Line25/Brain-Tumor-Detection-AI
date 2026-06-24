from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.api.deps import AdminUser, DbSession
from app.models.audit_log import AuditAction
from app.schemas.common import MessageResponse, PaginatedResponse, PaginationParams
from app.schemas.user import (
    PasswordResetByAdmin,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.services.user_service import UserService
from app.services.audit_service import AuditService


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    data: UserCreate,
    request: Request,
    db: DbSession,
    current_admin: AdminUser,
) -> UserRead:
    """
    Admin tạo tài khoản mới cho bác sĩ hoặc admin khác.

    Password sẽ được hash trong UserService trước khi lưu database.
    """

    try:
        user = UserService(db).create(data)
        AuditService(db).log_request(
            request=request,
            action=AuditAction.create_user,
            actor=current_admin,
            entity_type="user",
            entity_id=user.id,
            metadata={
                "username": user.username,
                "role": user.role.value,
            },
        )
        db.commit()
        db.refresh(user)
        return UserRead.model_validate(user)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=PaginatedResponse[UserRead],
    status_code=status.HTTP_200_OK,
)
def list_users(
    db: DbSession,
    _: AdminUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    only_active: bool | None = Query(default=None),
) -> PaginatedResponse[UserRead]:
    """
    Admin xem danh sách user có phân trang.

    keyword tìm theo username, email hoặc full_name.
    """

    pagination = PaginationParams(page=page, page_size=page_size)

    result = UserService(db).list_users(
        pagination=pagination,
        keyword=keyword,
        only_active=only_active,
    )

    return PaginatedResponse[UserRead].create(
        items=[UserRead.model_validate(user) for user in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
)
def get_user(
    user_id: UUID,
    db: DbSession,
    _: AdminUser,
) -> UserRead:
    """
    Admin xem chi tiết một user.
    """

    user = UserService(db).get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserRead.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
)
def update_user(
    user_id: UUID,
    data: UserUpdate,
    request: Request,
    db: DbSession,
    current_admin: AdminUser,
) -> UserRead:
    """
    Admin cập nhật thông tin user.

    Có thể cập nhật:
    - email,
    - full_name,
    - role,
    - is_active.
    """

    service = UserService(db)
    user = service.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    try:
        updated_user = service.update(user, data)
        AuditService(db).log_request(
            request=request,
            action=AuditAction.update_user,
            actor=current_admin,
            entity_type="user",
            entity_id=updated_user.id,
            metadata={
                "updated_fields": sorted(
                    data.model_dump(exclude_unset=True).keys()
                ),
            },
        )
        db.commit()
        db.refresh(updated_user)
        return UserRead.model_validate(updated_user)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{user_id}/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
def reset_password(
    user_id: UUID,
    data: PasswordResetByAdmin,
    request: Request,
    db: DbSession,
    current_admin: AdminUser,
) -> MessageResponse:
    """
    Admin đặt lại mật khẩu cho user.

    Không trả mật khẩu/hash trong response.
    """

    service = UserService(db)
    user = service.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    service.reset_password_by_admin(
        user=user,
        new_password=data.new_password,
    )
    AuditService(db).log_request(
        request=request,
        action=AuditAction.reset_password,
        actor=current_admin,
        entity_type="user",
        entity_id=user.id,
        metadata={"username": user.username},
    )
    db.commit()

    return MessageResponse(message="Password has been reset successfully")


@router.post(
    "/{user_id}/activate",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
)
def activate_user(
    user_id: UUID,
    request: Request,
    db: DbSession,
    current_admin: AdminUser,
) -> UserRead:
    """
    Admin mở khóa tài khoản user.
    """

    service = UserService(db)
    user = service.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    activated_user = service.activate(user)
    AuditService(db).log_request(
        request=request,
        action=AuditAction.activate_user,
        actor=current_admin,
        entity_type="user",
        entity_id=activated_user.id,
        metadata={"username": activated_user.username},
    )
    db.commit()
    db.refresh(activated_user)

    return UserRead.model_validate(activated_user)


@router.post(
    "/{user_id}/deactivate",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
)
def deactivate_user(
    user_id: UUID,
    request: Request,
    db: DbSession,
    current_admin: AdminUser,
) -> UserRead:
    """
    Admin khóa tài khoản user.

    Không xóa user khỏi database để giữ lịch sử dự đoán/audit log.
    """

    service = UserService(db)
    user = service.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    deactivated_user = service.deactivate(user)
    AuditService(db).log_request(
        request=request,
        action=AuditAction.deactivate_user,
        actor=current_admin,
        entity_type="user",
        entity_id=deactivated_user.id,
        metadata={"username": deactivated_user.username},
    )
    db.commit()
    db.refresh(deactivated_user)

    return UserRead.model_validate(deactivated_user)
