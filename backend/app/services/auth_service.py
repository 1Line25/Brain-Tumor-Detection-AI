from __future__ import annotations
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.user import UserRead
from app.services.user_service import UserService


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

    def login(self, data: LoginRequest) -> LoginResponse:
        """
        Đăng nhập và trả access token.

        Sau khi xác thực thành công:
        - Cập nhật last_login_at.
        - Tạo JWT chứa sub = user.id.
        - Trả token + thông tin user cho frontend.
        """

        user = self.authenticate(data)

        self.user_service.mark_login_success(user)

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