"""
Export tập trung các service của backend.

Mục đích:
- Giúp router import ngắn gọn hơn.
- Giữ tầng service tách biệt khỏi router/API.
- Không chạy logic nặng tại đây để tránh load model AI khi chỉ import package.

Ví dụ:
    from app.services import AuthService, PredictionService
"""

from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.gradcam_service import GradCAMService
from app.services.model_service import ModelPrediction, ModelService
from app.services.patient_service import PatientService
from app.services.prediction_service import PredictionService
from app.services.storage_service import StorageService
from app.services.user_service import UserService

__all__ = [
    "AuditService",
    "AuthService",
    "GradCAMService",
    "ModelPrediction",
    "ModelService",
    "PatientService",
    "PredictionService",
    "StorageService",
    "UserService",
]
