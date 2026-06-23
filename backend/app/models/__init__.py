"""
Import tập trung toàn bộ SQLAlchemy models.

Mục đích:
- Giúp Alembic nhìn thấy đầy đủ metadata khi tạo migration.
- Giúp các module khác import model gọn hơn.
- Tránh tình trạng quên import model làm thiếu bảng trong database.

Lưu ý tối ưu:
- File này chỉ import class model, không chạy logic nặng.
- Không import service/inference ở đây để tránh load model AI khi chỉ cần thao tác DB.
"""

from app.models.audit_log import AuditAction, AuditLog
from app.models.patient import Patient, PatientSex
from app.models.prediction import Prediction, PredictionStatus, TumorClass
from app.models.user import User, UserRole

__all__ = [
    "AuditAction",
    "AuditLog",
    "Patient",
    "PatientSex",
    "Prediction",
    "PredictionStatus",
    "TumorClass",
    "User",
    "UserRole",
]