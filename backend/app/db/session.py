from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()


# Engine được tạo một lần khi backend khởi động.
# Không tạo engine trong từng request vì việc mở lại connection
# liên tục sẽ làm tăng thời gian phản hồi và tải PostgreSQL.
engine: Engine = create_engine(
    settings.database_url,

    # Kiểm tra connection trước khi lấy từ pool.
    # Nếu PostgreSQL đã đóng connection cũ, SQLAlchemy sẽ tự tạo
    # connection mới thay vì để request đầu tiên bị lỗi.
    pool_pre_ping=True,

    # Giới hạn số connection thường trực.
    pool_size=settings.database_pool_size,

    # Số connection tạm thời được phép vượt giới hạn pool_size.
    max_overflow=settings.database_max_overflow,

    # Thu hồi connection lâu hơn 30 phút.
    # Hữu ích khi PostgreSQL hoặc proxy có giới hạn idle timeout.
    pool_recycle=1800,

    # Không in câu SQL trong production vì có thể làm lộ dữ liệu.
    echo=settings.debug,

    # PostgreSQL tự quản lý transaction.
    # Không bật autocommit để tránh lưu dữ liệu dở dang.
    isolation_level="READ COMMITTED",
)


# expire_on_commit=False giúp API vẫn đọc được object sau commit
# mà không cần gửi thêm một truy vấn SQL.
#
# autoflush=False tránh SQLAlchemy tự gửi câu SQL ở thời điểm
# chưa mong muốn. Service sẽ chủ động gọi flush hoặc commit.
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    Cung cấp một database session cho mỗi request FastAPI.

    Nếu request thành công:
        Service chịu trách nhiệm commit thay đổi.

    Nếu request xảy ra lỗi:
        rollback để không lưu transaction chưa hoàn chỉnh.

    Sau cùng:
        đóng session và trả connection về pool.
    """

    db = SessionLocal()

    try:
        yield db
    except Exception:
        # Rollback đảm bảo các thay đổi chưa hoàn chỉnh không bị lưu.
        db.rollback()
        raise
    finally:
        # close() trả connection về pool, không hủy connection vật lý.
        # Việc tái sử dụng connection giúp giảm thời gian kết nối.
        db.close()


def check_database_connection() -> bool:
    """
    Kiểm tra backend có kết nối được PostgreSQL hay không.

    Hàm này sẽ được endpoint /health sử dụng sau này.
    SELECT 1 rất nhẹ và không đọc dữ liệu nghiệp vụ.
    """

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return True
    except Exception:
        return False


def close_database_connections() -> None:
    """
    Đóng toàn bộ connection pool khi FastAPI shutdown.

    Hàm này giúp backend thoát sạch khi Docker container dừng.
    """

    engine.dispose()