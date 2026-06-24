from __future__ import annotations
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.user import UserRead
from app.services.login_throttle_service import (
    LoginThrottleService,
    LoginThrottleStatus,
)
from app.services.user_service import UserService


class LoginRateLimitError(ValueError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Too many failed login attempts. Try again later.")
        self.retry_after_seconds = retry_after_seconds


class AuthService:
    """
    Service xử lý nghiệp vụ xác thực.

    Tối ưu thiết kế:
    - Router auth không cần biết chi tiết kiểm tra password/token.
    - Tái sử dụng UserService để tránh lặp query user.
    - Tách riêng auth logic giúp dễ thay đổi về sau nếu muốn thêm refresh token.
    """

    def __init__(self, db: Session):
        """
        db là database session được inject từ FastAPI dependency.
        """

        self.db = db
        self.user_service = UserService(db)
        self.login_throttle_service = LoginThrottleService(db)

    def authenticate(self, data: LoginRequest) -> User:
        """
        Kiểm tra thông tin đăng nhập.

        Quy trình:
        1. Tìm user bằng username hoặc email.
        2. Kiểm tra user có tồn tại không.
        3. Kiểm tra tài khoản còn active không.
        4. Kiểm tra password.
        """

        user = self.user_service.get_by_identifier(data.identifier)

        if user is None:
            # Không nói rõ username/email sai để tránh lộ thông tin tài khoản.
            raise ValueError("Invalid username/email or password")

        if not user.is_active:
            raise ValueError("User account is inactive")

        if not verify_password(data.password, user.password_hash):
            # Cùng message với user not found để giảm khả năng dò tài khoản.
            raise ValueError("Invalid username/email or password")

        return user

    def login(
        self,
        data: LoginRequest,
        *,
        client_ip: str,
    ) -> LoginResponse:
        """
        Đăng nhập và trả access token.

        Sau khi xác thực thành công:
        - Cập nhật last_login_at.
        - Tạo JWT chứa sub = user.id.
        - Trả token + thông tin user cho frontend.
        """

        user = self.user_service.get_by_identifier(data.identifier)
        self.login_throttle_service.cleanup_stale_records()
        account_key = self.login_throttle_service.build_account_key(
            user_id=str(user.id) if user is not None else None,
            identifier=data.identifier,
        )
        ip_key = self.login_throttle_service.build_ip_key(client_ip)

        self._raise_if_blocked(
            self.login_throttle_service.check(
                scope_type="account",
                scope_key=account_key,
            )
        )
        self._raise_if_blocked(
            self.login_throttle_service.check(
                scope_type="ip",
                scope_key=ip_key,
            )
        )

        try:
            user = self.authenticate(data)
        except ValueError:
            account_status = self.login_throttle_service.register_failure(
                scope_type="account",
                scope_key=account_key,
                max_attempts=self.login_throttle_service.settings.login_max_failed_attempts,
            )
            ip_status = self.login_throttle_service.register_failure(
                scope_type="ip",
                scope_key=ip_key,
                max_attempts=self.login_throttle_service.settings.login_ip_max_failed_attempts,
            )
            blocked_status = self._most_restrictive(
                account_status,
                ip_status,
            )
            if blocked_status.blocked:
                raise LoginRateLimitError(
                    blocked_status.retry_after_seconds
                )
            raise

        self.user_service.mark_login_success(user)
        self.login_throttle_service.clear(
            account_key=account_key,
            ip_key=ip_key,
        )

        access_token = create_access_token(
            subject=str(user.id),
            extra_claims={  
                # Thêm role vào token để một số kiểm tra phía frontend tiện hơn.
                # Backend vẫn phải kiểm tra role từ DB khi bảo vệ API quan trọng.
                "role": user.role.value,
            },
        )

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserRead.model_validate(user),
        )

    @staticmethod
    def _raise_if_blocked(status: LoginThrottleStatus) -> None:
        if status.blocked:
            raise LoginRateLimitError(status.retry_after_seconds)

    @staticmethod
    def _most_restrictive(
        *statuses: LoginThrottleStatus,
    ) -> LoginThrottleStatus:
        blocked_statuses = [
            status for status in statuses if status.blocked
        ]
        if not blocked_statuses:
            return LoginThrottleStatus(blocked=False)
        return max(
            blocked_statuses,
            key=lambda status: status.retry_after_seconds,
        )

    def get_current_user_from_token(self, token_subject: str) -> User:
        try:
            user_id = UUID(token_subject)
        except ValueError as exc:
            raise ValueError("Invalid token subject") from exc

        user = self.user_service.get_by_id(user_id)

        if user is None:
            raise ValueError("User not found")

        if not user.is_active:
            raise ValueError("User account is inactive")

        return user
