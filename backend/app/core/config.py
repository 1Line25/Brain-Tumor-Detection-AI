from __future__ import annotations

from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# config.py nằm tại: backend/app/core/config.py
# parents[3] tương ứng với thư mục gốc của dự án trên host.
# Nhưng trong Docker, root là /app, tương ứng với parents[2].
if Path("/app/app/core/config.py").exists():
    PROJECT_ROOT = Path("/app")
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """
    Cấu hình dùng chung cho toàn bộ backend.

    Các giá trị ở đây có thể override bằng biến môi trường hoặc file .env.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Brain Tumor MRI Classification System"
    app_version: str = "1.0.0"

    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    log_level: Literal["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_to_file: bool = False

    # Prefix API thống nhất, ví dụ: /api/v1/auth/login.
    api_v1_prefix: str = "/api/v1"

    # PostgreSQL connection URL.
    database_url: str = (
        "postgresql+psycopg://admin:admin123@localhost:5432/mydatabase"
    )
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=100)

    # Backend dùng model EfficientNetB0 tốt nhất đã train ở thư mục gốc.
    model_path: Path = PROJECT_ROOT / "best_tl_model.h5"

    # Notebook train của dự án dùng IMG_SIZE = (240, 240).
    model_input_size: tuple[int, int] = (240, 240)

    # Thứ tự label phải khớp class_indices khi train:
    # {'glioma_tumor': 0, 'meningioma_tumor': 1, 'no_tumor': 2, 'pituitary_tumor': 3}
    model_labels: tuple[str, ...] = (
        "glioma_tumor",
        "meningioma_tumor",
        "no_tumor",
        "pituitary_tumor",
    )

    # Conv2D cuối của EfficientNetB0. GradCAMService vẫn tự tìm fallback nếu
    # kiến trúc model hoặc tên layer thay đổi.
    gradcam_last_conv_layer_name: str = "top_conv"

    # Storage lưu ảnh MRI và Grad-CAM.
    storage_root: Path = PROJECT_ROOT / "storage"
    mri_storage_directory: str = "mri"
    gradcam_storage_directory: str = "gradcam"

    # Tự động xóa file MRI và Grad-CAM sau 24 giờ.
    image_retention_hours: int = Field(default=24, ge=1, le=168)

    # Giới hạn upload để tránh file quá lớn chiếm RAM/ổ đĩa.
    max_upload_size_mb: int = Field(default=10, ge=1, le=50)

    allowed_image_extensions: tuple[str, ...] = (
        ".jpg",
        ".jpeg",
        ".png",
    )
    allowed_image_mime_types: tuple[str, ...] = (
        "image/jpeg",
        "image/png",
    )

    # JWT configuration.
    secret_key: SecretStr = SecretStr("development-only-change-this-secret-key")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)

    # Bảo vệ đăng nhập: khóa theo tài khoản và IP sau nhiều lần thử sai.
    login_max_failed_attempts: int = Field(default=5, ge=3, le=20)
    login_ip_max_failed_attempts: int = Field(default=20, ge=5, le=200)
    login_attempt_window_minutes: int = Field(default=15, ge=1, le=1440)
    login_lockout_minutes: int = Field(default=15, ge=1, le=1440)

    # Frontend HTML/CSS/JS local được phép gọi API.
    cors_origins: tuple[str, ...] = (
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )

    @property
    def project_root(self) -> Path:
        """Trả về thư mục gốc dự án."""

        return PROJECT_ROOT

    @property
    def storage_dir(self) -> Path:
        """Alias thống nhất cho thư mục storage."""

        return self.storage_root

    @property
    def mri_storage_dir(self) -> Path:
        """Thư mục lưu ảnh MRI gốc."""

        return self.storage_root / self.mri_storage_directory

    @property
    def gradcam_storage_dir(self) -> Path:
        """Thư mục lưu ảnh Grad-CAM."""

        return self.storage_root / self.gradcam_storage_directory

    @property
    def mri_storage_path(self) -> Path:
        """Alias giữ tương thích với code đã viết trước đó."""

        return self.mri_storage_dir

    @property
    def gradcam_storage_path(self) -> Path:
        """Alias giữ tương thích với code đã viết trước đó."""

        return self.gradcam_storage_dir

    @property
    def storage_retention_delta(self) -> timedelta:
        """Khoảng thời gian giữ file MRI/Grad-CAM trước khi cleanup."""

        return timedelta(hours=self.image_retention_hours)

    @property
    def max_upload_size_bytes(self) -> int:
        """Chuyển giới hạn upload từ MB sang bytes."""

        return self.max_upload_size_mb * 1024 * 1024

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Kiểm tra secret production và quan hệ giữa các ngưỡng bảo mật."""

        default_secret = "development-only-change-this-secret-key"

        if (
            self.environment == "production"
            and self.secret_key.get_secret_value() == default_secret
        ):
            raise ValueError("SECRET_KEY must be changed in production.")

        if self.login_ip_max_failed_attempts < self.login_max_failed_attempts:
            raise ValueError(
                "LOGIN_IP_MAX_FAILED_ATTEMPTS must be greater than or equal "
                "to LOGIN_MAX_FAILED_ATTEMPTS."
            )

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Chỉ tạo Settings một lần.

    Cache giúp tránh đọc và parse .env lại ở mỗi request.
    """

    return Settings()


# Giữ alias này để các file cũ `from app.core.config import settings`
# không bị lỗi trong lúc refactor dần sang get_settings().
settings = get_settings()
