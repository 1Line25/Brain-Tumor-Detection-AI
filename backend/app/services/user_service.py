from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """
    Service xử lý nghiệp vụ liên quan đến User.

    Tối ưu thiết kế:
    - Router không thao tác database trực tiếp quá nhiều.
    - Gom logic user vào một nơi để dễ bảo trì và test.
    - Dùng select rõ ràng của SQLAlchemy 2.x thay vì query cũ.
    """

    def __init__(self, db: Session):
        """
        db là database session được FastAPI inject từ dependency get_db().
        """

        self.db = db

    def get_by_id(self, user_id: UUID) -> User | None:
        """
        Lấy user theo ID.

        Dùng cho:
        - Auth dependency lấy current_user.
        - Admin xem chi tiết user.
        """

        statement = select(User).where(User.id == user_id)
        return self.db.scalar(statement)

    def get_by_username(self, username: str) -> User | None:
        """
        Lấy user theo username.

        Username được normalize lowercase để tránh lệch dữ liệu.
        """

        normalized_username = username.strip().lower()

        statement = select(User).where(User.username == normalized_username)
        return self.db.scalar(statement)

    def get_by_email(self, email: str) -> User | None:
        """
        Lấy user theo email.

        Email được normalize lowercase để so sánh nhất quán.
        """

        normalized_email = email.strip().lower()

        statement = select(User).where(User.email == normalized_email)
        return self.db.scalar(statement)

    def get_by_identifier(self, identifier: str) -> User | None:
        """
        Lấy user bằng username hoặc email.

        Dùng cho form đăng nhập một ô:
        - username
        - hoặc email
        """

        normalized_identifier = identifier.strip().lower()

        statement = select(User).where(
            or_(
                User.username == normalized_identifier,
                User.email == normalized_identifier,
            )
        )

        return self.db.scalar(statement)

    def create(self, data: UserCreate) -> User:
        """
        Tạo user mới.

        Lưu ý tối ưu/bảo mật:
        - Không bao giờ lưu password thô.
        - Hash password ở service layer.
        - Flush sớm để bắt lỗi unique username/email ngay tại đây.
        """

        user = User(
            username=data.username,
            email=str(data.email),
            password_hash=get_password_hash(data.password),
            full_name=data.full_name,
            role=data.role,
            is_active=True,
        )

        self.db.add(user)

        try:
            # flush đưa câu lệnh INSERT xuống DB nhưng chưa commit.
            # Router hoặc unit-of-work bên ngoài có thể quyết định commit.
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()

            # Không trả lỗi kỹ thuật DB trực tiếp cho frontend.
            # Router sau này có thể bắt ValueError và đổi thành HTTP 400.
            raise ValueError("Username or email already exists") from exc

        return user

    def update(self, user: User, data: UserUpdate) -> User:
        """
        Cập nhật thông tin user.

        Chỉ cập nhật field nào frontend gửi lên.
        """

        update_data = data.model_dump(exclude_unset=True)

        if "email" in update_data and update_data["email"] is not None:
            update_data["email"] = str(update_data["email"]).strip().lower()

        for field, value in update_data.items():
            setattr(user, field, value)

        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError("Email already exists") from exc

        return user

    def change_password(
        self,
        *,
        user: User,
        old_password: str,
        new_password: str,
    ) -> None:
        """
        Đổi mật khẩu cho user đang đăng nhập.

        Backend phải kiểm tra old_password để tránh người khác
        dùng phiên đăng nhập chưa khóa màn hình rồi đổi mật khẩu.
        """

        if not verify_password(old_password, user.password_hash):
            raise ValueError("Old password is incorrect")

        user.password_hash = get_password_hash(new_password)
        self.db.flush()

    def reset_password_by_admin(
        self,
        *,
        user: User,
        new_password: str,
    ) -> None:
        """
        Admin đặt lại mật khẩu cho user khác.

        Không cần old_password vì quyền này chỉ dành cho admin.
        """

        user.password_hash = get_password_hash(new_password)
        self.db.flush()

    def deactivate(self, user: User) -> User:
        """
        Khóa tài khoản user.

        Không xóa user khỏi DB vì cần giữ lịch sử:
        - prediction
        - audit log
        - patient created_by
        """

        user.is_active = False
        self.db.flush()
        return user

    def activate(self, user: User) -> User:
        """
        Mở khóa tài khoản user.
        """

        user.is_active = True
        self.db.flush()
        return user

    def mark_login_success(self, user: User) -> None:
        """
        Cập nhật thời điểm đăng nhập thành công.

        Dùng timezone-aware datetime để tránh lệch giờ khi deploy Docker/server.
        """

        user.last_login_at = datetime.now(timezone.utc)
        self.db.flush()

    def list_users(
        self,
        *,
        pagination: PaginationParams,
        keyword: str | None = None,
        only_active: bool | None = None,
    ) -> PaginatedResponse[User]:
        """
        Lấy danh sách user có phân trang.

        Tối ưu:
        - Query count riêng để frontend biết tổng số bản ghi.
        - Giới hạn page_size trong PaginationParams để tránh query quá nặng.
        - Keyword tìm theo username/email/full_name.
        """

        filters = []

        if keyword:
            normalized_keyword = f"%{keyword.strip().lower()}%"
            filters.append(
                or_(
                    User.username.ilike(normalized_keyword),
                    User.email.ilike(normalized_keyword),
                    User.full_name.ilike(normalized_keyword),
                )
            )

        if only_active is not None:
            filters.append(User.is_active.is_(only_active))

        total_statement = select(func.count()).select_from(User)

        list_statement = (
            select(User)
            .order_by(User.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )

        if filters:
            total_statement = total_statement.where(*filters)
            list_statement = list_statement.where(*filters)

        total = self.db.scalar(total_statement) or 0
        items = list(self.db.scalars(list_statement).all())

        return PaginatedResponse[User].create(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )