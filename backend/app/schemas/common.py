from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class MessageResponse(BaseModel):
    """
    Response đơn giản cho các API chỉ cần trả về thông báo.

    Ví dụ:
    - Đăng xuất thành công
    - Xóa file hết hạn thành công
    - Cập nhật thông tin thành công
    """

    message: str = Field(
        ...,
        examples=["Operation completed successfully"],
    )


class ErrorResponse(BaseModel):
    """
    Response lỗi chuẩn hóa.

    Frontend có thể dựa vào format này để hiển thị lỗi thống nhất,
    thay vì mỗi API trả lỗi một kiểu khác nhau.
    """

    detail: str = Field(
        ...,
        examples=["Invalid username or password"],
    )


class PaginationParams(BaseModel):
    """
    Tham số phân trang dùng chung.

    Tối ưu:
    - Giới hạn page_size tối đa để tránh frontend request quá nhiều dữ liệu một lần.
    - Dùng page bắt đầu từ 1 để thân thiện với giao diện người dùng.
    """

    page: int = Field(
        default=1,
        ge=1,
        description="Trang hiện tại, bắt đầu từ 1",
    )

    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Số bản ghi mỗi trang, tối đa 100",
    )

    @property
    def offset(self) -> int:
        """
        Tính offset cho database query.

        Ví dụ:
        page = 1, page_size = 20 => offset = 0
        page = 2, page_size = 20 => offset = 20
        """

        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Response danh sách có phân trang.

    Dùng Generic[T] để tái sử dụng cho nhiều loại dữ liệu:
    - PaginatedResponse[UserRead]
    - PaginatedResponse[PatientRead]
    - PaginatedResponse[PredictionRead]
    """

    items: list[T] = Field(
        default_factory=list,
        description="Danh sách bản ghi của trang hiện tại",
    )

    total: int = Field(
        ...,
        ge=0,
        description="Tổng số bản ghi phù hợp với điều kiện lọc",
    )

    page: int = Field(
        ...,
        ge=1,
        description="Trang hiện tại",
    )

    page_size: int = Field(
        ...,
        ge=1,
        description="Số bản ghi mỗi trang",
    )

    total_pages: int = Field(
        ...,
        ge=0,
        description="Tổng số trang",
    )

    @classmethod
    def create(
        cls,
        *,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        """
        Helper tạo response phân trang.

        Tối ưu:
        - Gom công thức tính total_pages vào một nơi.
        - Tránh mỗi API tự tính phân trang một kiểu.
        """

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )