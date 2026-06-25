"""
Export tập trung toàn bộ Pydantic schemas.

Mục đích:
- Giúp router/service import gọn hơn.
- Tránh import vòng lặp bằng cách chỉ import schema, không import service/router.
- Giúp cấu trúc backend rõ ràng hơn khi dự án lớn dần.

Ví dụ:
    from app.schemas import UserRead, PatientCreate, PredictionResult
"""

from app.schemas.auth import CurrentUserResponse, LoginRequest, LoginResponse, TokenResponse
from app.schemas.audit_log import AuditLogFilter, AuditLogRead
from app.schemas.common import (
    ErrorResponse,
    MessageResponse,
    PaginatedResponse,
    PaginationParams,
)
from app.schemas.patient import (
    PatientCreate,
    PatientDetail,
    PatientDuplicateCheck,
    PatientDuplicateResult,
    PatientRead,
    PatientSummary,
    PatientUpdate,
)
from app.schemas.dashboard import DashboardStatistics, TumorClassStatistic
from app.schemas.prediction import (
    PredictionCreate,
    PredictionDetail,
    PredictionFailed,
    PredictionFilter,
    PredictionRead,
    PredictionReviewUpdate,
    PredictionResult,
)
from app.schemas.user import (
    PasswordChange,
    PasswordResetByAdmin,
    UserCreate,
    UserRead,
    UserSummary,
    UserUpdate,
)

__all__ = [
    "CurrentUserResponse",
    "DashboardStatistics",
    "AuditLogFilter",
    "AuditLogRead",
    "ErrorResponse",
    "LoginRequest",
    "LoginResponse",
    "MessageResponse",
    "PaginatedResponse",
    "PaginationParams",
    "PasswordChange",
    "PasswordResetByAdmin",
    "PatientCreate",
    "PatientDetail",
    "PatientDuplicateCheck",
    "PatientDuplicateResult",
    "PatientRead",
    "PatientSummary",
    "PatientUpdate",
    "PredictionCreate",
    "PredictionDetail",
    "PredictionFailed",
    "PredictionFilter",
    "PredictionRead",
    "PredictionReviewUpdate",
    "PredictionResult",
    "TokenResponse",
    "TumorClassStatistic",
    "UserCreate",
    "UserRead",
    "UserSummary",
    "UserUpdate",
]
