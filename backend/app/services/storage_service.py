from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings


class StorageService:
    """
    Service quản lý file trong thư mục storage.

    Database chỉ lưu đường dẫn tương đối, còn file thật nằm trong:
    - storage/mri
    - storage/gradcam
    """

    def __init__(self) -> None:
        self.settings = get_settings()

        # Tự tạo folder khi backend chạy, giúp Docker/demo không cần chuẩn bị tay.
        self.settings.storage_dir.mkdir(parents=True, exist_ok=True)
        self.settings.mri_storage_dir.mkdir(parents=True, exist_ok=True)
        self.settings.gradcam_storage_dir.mkdir(parents=True, exist_ok=True)

    async def save_upload_file(
        self,
        *,
        upload_file: UploadFile,
        folder: str = "mri",
    ) -> Path:
        """
        Lưu file upload vào storage và trả về relative path.

        Tối ưu:
        - Copy theo stream thay vì đọc toàn bộ file vào RAM.
        - Tên file dùng UUID để tránh trùng và tránh lộ tên file gốc.
        """

        self._validate_upload_file(upload_file)

        target_dir = self._get_daily_folder(folder)
        target_dir.mkdir(parents=True, exist_ok=True)

        extension = self._get_safe_extension(upload_file.filename)
        filename = f"{uuid4().hex}{extension}"
        absolute_path = target_dir / filename

        try:
            self._copy_upload_file_with_limit(
                upload_file=upload_file,
                target_path=absolute_path,
            )
            self._validate_saved_image(absolute_path)
        except Exception:
            # Nếu copy lỗi giữa chừng, xóa file dở dang để storage không bị rác.
            if absolute_path.exists():
                absolute_path.unlink()
            raise

        return self.to_relative_path(absolute_path)

    def save_bytes(
        self,
        *,
        data: bytes,
        folder: str,
        extension: str = ".png",
    ) -> Path:
        """
        Lưu dữ liệu bytes ra file.

        Dùng cho Grad-CAM vì ảnh Grad-CAM được tạo trong backend.
        """

        target_dir = self._get_daily_folder(folder)
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_extension = extension if extension.startswith(".") else f".{extension}"
        filename = f"{uuid4().hex}{safe_extension.lower()}"
        absolute_path = target_dir / filename

        absolute_path.write_bytes(data)

        return self.to_relative_path(absolute_path)

    def delete_file(self, relative_path: str | Path | None) -> bool:
        """
        Xóa một file theo relative path.

        Có kiểm tra path nằm trong storage để tránh path traversal.
        """

        if not relative_path:
            return False

        absolute_path = self.to_absolute_path(relative_path)

        if not self._is_inside_storage(absolute_path):
            raise ValueError("Unsafe file path outside storage directory")

        if not absolute_path.exists():
            return False

        if absolute_path.is_file():
            absolute_path.unlink()
            return True

        return False

    def to_absolute_path(self, relative_path: str | Path) -> Path:
        """
        Chuyển relative path trong DB thành absolute path trên server.
        """

        path = Path(relative_path)

        if path.is_absolute():
            return path.resolve()

        return (self.settings.project_root / path).resolve()

    def to_relative_path(self, absolute_path: str | Path) -> Path:
        """
        Chuyển absolute path thành relative path so với project root.
        """

        path = Path(absolute_path).resolve()
        return path.relative_to(self.settings.project_root)

    def build_expiration_time(self) -> datetime:
        """
        Tạo thời điểm hết hạn file.

        Mặc định theo config là sau 24 giờ.
        """

        return datetime.now(timezone.utc) + self.settings.storage_retention_delta

    def _validate_upload_file(self, upload_file: UploadFile) -> None:
        """
        Validate file upload cơ bản.

        Kiểm tra MIME type và extension để tránh upload file không phải ảnh.
        """

        if upload_file.content_type not in self.settings.allowed_image_mime_types:
            raise ValueError("Only JPG and PNG images are allowed")

        extension = self._get_safe_extension(upload_file.filename)

        if extension not in self.settings.allowed_image_extensions:
            raise ValueError("Only .jpg, .jpeg and .png files are allowed")

    def _copy_upload_file_with_limit(
        self,
        *,
        upload_file: UploadFile,
        target_path: Path,
    ) -> None:
        """
        Copy file upload xuống ổ đĩa và kiểm soát dung lượng thật.

        Lý do không dùng shutil.copyfileobj trực tiếp:
        - copyfileobj không tự chặn file quá lớn,
        - nếu frontend upload file rất lớn có thể chiếm đầy ổ đĩa.
        """

        max_size = self.settings.max_upload_size_bytes
        copied_size = 0
        chunk_size = 1024 * 1024

        # Đảm bảo đọc từ đầu file.
        upload_file.file.seek(0)

        with target_path.open("wb") as buffer:
            while True:
                chunk = upload_file.file.read(chunk_size)

                if not chunk:
                    break

                copied_size += len(chunk)

                if copied_size > max_size:
                    raise ValueError(
                        f"File is too large. Maximum size is "
                        f"{self.settings.max_upload_size_mb} MB"
                    )

                buffer.write(chunk)

    def _validate_saved_image(self, image_path: Path) -> None:
        """
        Kiểm tra nội dung file có thật sự là ảnh hợp lệ không.

        MIME type và extension có thể bị giả mạo, nên cần mở file bằng Pillow
        sau khi lưu để chặn file không phải ảnh.
        """

        try:
            with Image.open(image_path) as image:
                image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError("Uploaded file is not a valid image") from exc

    def _get_daily_folder(self, folder: str) -> Path:
        """
        Tạo folder lưu file theo ngày.

        Ví dụ:
        storage/mri/2026/06/23/
        storage/gradcam/2026/06/23/
        """

        now = datetime.now(timezone.utc)

        if folder == "mri":
            base_dir = self.settings.mri_storage_dir
        elif folder == "gradcam":
            base_dir = self.settings.gradcam_storage_dir
        else:
            raise ValueError("Unsupported storage folder")

        return base_dir / f"{now.year:04d}" / f"{now.month:02d}" / f"{now.day:02d}"

    def _get_safe_extension(self, filename: str | None) -> str:
        """
        Lấy extension an toàn từ filename.

        Không dùng filename gốc làm tên file lưu trữ.
        """

        if not filename:
            raise ValueError("File name is required")

        return Path(filename).suffix.lower()

    def _is_inside_storage(self, absolute_path: Path) -> bool:
        """
        Kiểm tra path có nằm trong storage_dir không trước khi xóa file.
        """

        storage_root = self.settings.storage_dir.resolve()

        try:
            absolute_path.resolve().relative_to(storage_root)
            return True
        except ValueError:
            return False
