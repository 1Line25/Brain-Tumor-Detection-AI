from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import DbSession, DoctorOrAdminUser
from app.schemas.dashboard import DashboardStatistics
from app.services.dashboard_service import DashboardService


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/statistics",
    response_model=DashboardStatistics,
    status_code=status.HTTP_200_OK,
)
def get_dashboard_statistics(
    db: DbSession,
    current_user: DoctorOrAdminUser,
) -> DashboardStatistics:
    """Trả thống kê trong đúng phạm vi dữ liệu người dùng được phép xem."""

    return DashboardService(db).get_statistics(current_user=current_user)
