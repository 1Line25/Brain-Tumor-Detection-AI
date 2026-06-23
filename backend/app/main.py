from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

    yield

    close_database_connections()


def create_app() -> FastAPI:
    """
    Tạo FastAPI application.

    Tách create_app() giúp dễ test hơn và dễ mở rộng cấu hình sau này.
    """

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

    # Include toàn bộ API version 1.
    app.include_router(
        api_router,
        prefix=settings.api_v1_prefix,
    )

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
