from __future__ import annotations
import sys
from pathlib import Path
from time import perf_counter

from loguru import logger

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import check_database_connection, close_database_connections


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Quản lý vòng đời ứng dụng FastAPI.

    Startup:
    - hiện tại chưa load model ngay để app khởi động nhanh hơn.

    Shutdown:
    - đóng database connection pool để Docker/container dừng sạch.
    """
    logger.info("Backend FastAPI đang khởi động.")
    logger.info(
        "Database: {}.",
        "kết nối thành công" if check_database_connection() else "chưa thể kết nối",
    )
    logger.info(
        "Model inference: {} tại {}.",
        "đã sẵn sàng" if settings.model_path.exists() else "không tìm thấy",
        settings.model_path,
    )
    yield

    logger.info("Backend FastAPI đang dừng và đóng connection pool.")
    close_database_connections()
    logger.info("Backend FastAPI đã dừng an toàn.")


def create_app() -> FastAPI:
    """
    Tạo FastAPI application.

    Tách create_app() giúp dễ test hơn và dễ mở rộng cấu hình sau này.
    """
    
    # Configure Loguru
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    logger.remove()
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.log_level,
        colorize=True,
    )

    if settings.log_to_file:
        log_directory = Path("logs")
        log_directory.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_directory / "app.log",
            format=log_format,
            rotation="10 MB",
            retention="7 days",
            level=settings.log_level,
            encoding="utf-8",
        )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Cho phép frontend HTML/CSS/JS gọi API từ localhost.
    # Khi deploy thật, chỉ nên cho domain frontend chính thức.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_request(request: Request, call_next):
        start_time = perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (perf_counter() - start_time) * 1000
            logger.exception(
                "Request thất bại | phương_thức={} đường_dẫn={} thời_gian={:.2f}ms",
                request.method,
                request.url.path,
                elapsed_ms,
            )
            raise

        elapsed_ms = (perf_counter() - start_time) * 1000
        if request.url.path != "/health":
            logger.info(
                "Request hoàn tất | phương_thức={} đường_dẫn={} trạng_thái={} thời_gian={:.2f}ms",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
        return response

    # Include toàn bộ API version 1.
    app.include_router(
        api_router,
        prefix=settings.api_v1_prefix,
    )

    # Phục vụ file tĩnh (ảnh MRI, Grad-CAM)
    if not os.path.exists("storage"):
        os.makedirs("storage")
    app.mount("/storage", StaticFiles(directory="storage"), name="storage")

    @app.get("/health", tags=["Health"])
    def health_check() -> dict[str, object]:
        """
        Health check nhẹ cho Docker hoặc frontend kiểm tra backend còn sống không.

        Không load model ở đây vì model TensorFlow khá nặng.
        """

        database_ok = check_database_connection()

        return {
            "status": "ok" if database_ok else "degraded",
            "app": settings.app_name,
            "version": settings.app_version,
            "database": database_ok,
        }

    return app


app = create_app()
