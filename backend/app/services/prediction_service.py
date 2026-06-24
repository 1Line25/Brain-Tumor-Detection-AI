from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import UUID

from fastapi import UploadFile
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.patient import Patient
from app.models.prediction import Prediction, PredictionStatus
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.prediction import PredictionFilter
from app.services.gradcam_service import GradCAMService
from app.services.model_service import ModelService, ModelPrediction
from app.services.storage_service import StorageService


class PredictionService:
    """
    Service xử lý toàn bộ luồng dự đoán u não từ ảnh MRI.

    Nhiệm vụ chính:
    - Lưu ảnh MRI upload vào storage.
    - Gọi model EfficientNetB0 best_tl_model.h5 để phân loại.
    - Tạo ảnh Grad-CAM giải thích vùng model tập trung.
    - Ghi lịch sử dự đoán vào database.

    Tối ưu thiết kế:
    - Router chỉ gọi một hàm service, không tự xử lý nhiều bước phức tạp.
    - Database chỉ lưu đường dẫn ảnh, không lưu binary ảnh.
    - Nếu inference lỗi, vẫn ghi record failed để dễ debug/demo.
    """

    _inference_lock = Lock()

    def __init__(self, db: Session) -> None:
        """
        db là SQLAlchemy session được FastAPI inject từ dependency get_db().
        """

        self.db = db
        self.storage_service = StorageService()
        self.model_service = ModelService()
        self.gradcam_service = GradCAMService()

    def create_prediction(
        self,
        *,
        patient: Patient,
        doctor: User,
        upload_file: UploadFile,
    ) -> Prediction:
        """
        Tạo một lần dự đoán mới từ ảnh MRI upload.

        Quy trình:
        1. Lưu ảnh MRI vào storage/mri.
        2. Chạy model để lấy predicted_class, confidence, probabilities.
        3. Tạo Grad-CAM và lưu vào storage/gradcam.
        4. Ghi record prediction status=success.

        Nếu bước 2 hoặc 3 lỗi:
        - vẫn ghi record prediction status=failed,
        - lưu error_message,
        - giữ đường dẫn ảnh MRI để debug trong 24 giờ.
        """

        if (
            doctor.role == UserRole.doctor
            and patient.created_by != doctor.id
        ):
            raise PermissionError(
                "Doctor cannot create a prediction for another doctor's patient"
            )

        mri_relative_path = self.storage_service.save_upload_file(
            upload_file=upload_file,
            folder="mri",
        )

        expires_at = self.storage_service.build_expiration_time()
        mri_absolute_path = self.storage_service.to_absolute_path(mri_relative_path)

        try:
            # Model được dùng chung giữa các request. Chạy tuần tự vùng
            # inference + Grad-CAM để tránh tăng RAM và race condition.
            with self.__class__._inference_lock:
                model_prediction = self.model_service.predict(mri_absolute_path)
                gradcam_relative_path = self._generate_and_save_gradcam(
                    image_path=mri_absolute_path,
                    model_prediction=model_prediction,
                )

            prediction = Prediction(
                patient_id=patient.id,
                doctor_id=doctor.id,
                mri_image_path=str(mri_relative_path),
                gradcam_image_path=(
                    str(gradcam_relative_path) if gradcam_relative_path else None
                ),
                predicted_class=model_prediction.predicted_class,
                confidence=model_prediction.confidence,
                probabilities=model_prediction.probabilities,
                status=PredictionStatus.success,
                error_message=None,
                expires_at=expires_at,
                files_deleted=False,
            )

        except Exception as exc:
            logger.exception(
                "Dự đoán thất bại | patient_id={} doctor_id={}",
                patient.id,
                doctor.id,
            )
            # Không để lỗi inference làm mất hoàn toàn lịch sử thao tác.
            # Record failed giúp admin/dev biết request nào đã lỗi và lỗi gì.
            prediction = Prediction(
                patient_id=patient.id,
                doctor_id=doctor.id,
                mri_image_path=str(mri_relative_path),
                gradcam_image_path=None,
                predicted_class=None,
                confidence=None,
                probabilities=None,
                status=PredictionStatus.failed,
                error_message=str(exc),
                expires_at=expires_at,
                files_deleted=False,
            )

        self.db.add(prediction)

        try:
            self.db.flush()
        except Exception:
            # Nếu lưu DB thất bại sau khi đã ghi file, xóa file để tránh rác storage.
            self.storage_service.delete_file(prediction.mri_image_path)
            self.storage_service.delete_file(prediction.gradcam_image_path)
            raise

        return prediction

    def get_by_id(
        self,
        prediction_id: UUID,
        *,
        current_user: User,
    ) -> Prediction | None:
        """
        Lấy prediction theo ID trong phạm vi được phép.

        Admin được xem mọi prediction. Bác sĩ chỉ được xem prediction do
        chính mình thực hiện.
        """

        statement = select(Prediction).where(Prediction.id == prediction_id)
        statement = self._scope_to_current_user(statement, current_user)
        return self.db.scalar(statement)

    def get_detail_by_id(
        self,
        prediction_id: UUID,
        *,
        current_user: User,
    ) -> Prediction | None:
        """
        Lấy prediction kèm thông tin bệnh nhân và bác sĩ.

        Vì relationship trong model dùng lazy='raise',
        cần chủ động joinedload để lấy dữ liệu trong cùng một query.
        """

        statement = (
            select(Prediction)
            .options(
                joinedload(Prediction.patient),
                joinedload(Prediction.doctor),
            )
            .where(Prediction.id == prediction_id)
        )
        statement = self._scope_to_current_user(statement, current_user)

        return self.db.scalar(statement)

    def list_predictions(
        self,
        *,
        current_user: User,
        pagination: PaginationParams,
        filters: PredictionFilter | None = None,
    ) -> PaginatedResponse[Prediction]:
        """
        Lấy danh sách lịch sử dự đoán có phân trang và bộ lọc.

        Hỗ trợ lọc theo:
        - patient_id
        - doctor_id
        - predicted_class
        - status
        - khoảng thời gian tạo
        """

        conditions = self._build_filter_conditions(filters)

        if current_user.role == UserRole.doctor:
            conditions.append(Prediction.doctor_id == current_user.id)

        total_statement = select(func.count()).select_from(Prediction)

        list_statement = (
            select(Prediction)
            .options(
                joinedload(Prediction.patient),
                joinedload(Prediction.doctor),
            )
            .order_by(Prediction.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )

        if conditions:
            total_statement = total_statement.where(*conditions)
            list_statement = list_statement.where(*conditions)

        total = self.db.scalar(total_statement) or 0
        items = list(self.db.scalars(list_statement).all())

        return PaginatedResponse[Prediction].create(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    def _scope_to_current_user(self, statement, current_user: User):
        """
        Thêm điều kiện sở hữu vào query prediction.

        Bác sĩ chỉ thấy các lần dự đoán mình thực hiện. Admin không bị thêm
        điều kiện và có thể giám sát toàn hệ thống.
        """

        if current_user.role == UserRole.doctor:
            statement = statement.where(
                Prediction.doctor_id == current_user.id
            )

        return statement

    def delete_expired_files(self) -> int:
        """
        Xóa file MRI và Grad-CAM đã hết hạn 24 giờ.

        Lưu ý:
        - Chỉ xóa file vật lý trong storage.
        - Không xóa record prediction khỏi database để vẫn giữ lịch sử.
        - Trả về số prediction đã được đánh dấu files_deleted=True.
        """

        now = datetime.now(timezone.utc)

        statement = select(Prediction).where(
            Prediction.files_deleted.is_(False),
            Prediction.expires_at <= now,
        )

        expired_predictions = list(self.db.scalars(statement).all())

        for prediction in expired_predictions:
            self.storage_service.delete_file(prediction.mri_image_path)
            self.storage_service.delete_file(prediction.gradcam_image_path)

            prediction.files_deleted = True

        self.db.flush()

        return len(expired_predictions)

    def _generate_and_save_gradcam(
        self,
        *,
        image_path: Path,
        model_prediction: ModelPrediction,
    ) -> Path | None:
        """
        Tạo Grad-CAM và lưu xuống storage/gradcam.

        Nếu Grad-CAM lỗi, hàm sẽ raise exception để create_prediction
        ghi record failed. Với đồ án y tế, Grad-CAM là phần giải thích quan trọng,
        nên mình ưu tiên minh bạch lỗi thay vì âm thầm bỏ qua.
        """

        class_index = self._get_class_index(model_prediction)

        # Dùng model đã cache trong ModelService để tránh load lại file .h5.
        model = self.model_service.get_model()

        gradcam_bytes = self.gradcam_service.generate(
            model=model,
            image_path=image_path,
            class_index=class_index,
        )

        return self.storage_service.save_bytes(
            data=gradcam_bytes,
            folder="gradcam",
            extension=".png",
        )

    def _get_class_index(self, model_prediction: ModelPrediction) -> int:
        """
        Lấy index của predicted_class theo thứ tự label model.

        Grad-CAM cần class_index, không chỉ tên class.
        """

        label = model_prediction.predicted_class.value
        try:
            return self.model_service.labels.index(label)
        except ValueError as exc:
            raise ValueError(
                f"Predicted label '{label}' not found in model labels"
            ) from exc

    def _build_filter_conditions(
        self,
        filters: PredictionFilter | None,
    ) -> list:
        """
        Chuyển PredictionFilter thành danh sách điều kiện SQLAlchemy.

        Tách riêng hàm này để list_predictions gọn hơn và dễ mở rộng bộ lọc.
        """

        if filters is None:
            return []

        conditions = []

        if filters.patient_id is not None:
            conditions.append(Prediction.patient_id == filters.patient_id)

        if filters.doctor_id is not None:
            conditions.append(Prediction.doctor_id == filters.doctor_id)

        if filters.predicted_class is not None:
            conditions.append(Prediction.predicted_class == filters.predicted_class)

        if filters.status is not None:
            conditions.append(Prediction.status == filters.status)

        if filters.from_date is not None:
            conditions.append(Prediction.created_at >= filters.from_date)

        if filters.to_date is not None:
            conditions.append(Prediction.created_at <= filters.to_date)

        return conditions
