from __future__ import annotations

from uuid import UUID

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)

from app.api.deps import AdminUser, DbSession, DoctorOrAdminUser
from app.models.audit_log import AuditAction
from app.models.prediction import PredictionStatus, TumorClass
from app.schemas.common import MessageResponse, PaginatedResponse, PaginationParams
from app.schemas.prediction import (
    PredictionDetail,
    PredictionFilter,
    PredictionRead,
    PredictionResult,
)
from app.services.patient_service import PatientService
from app.services.prediction_service import PredictionService
from app.services.audit_service import AuditService


router = APIRouter(
    prefix="/predictions",
    tags=["Predictions"],
)


@router.post(
    "",
    response_model=PredictionResult | PredictionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_prediction(
    request: Request,
    db: DbSession,
    current_user: DoctorOrAdminUser,
    patient_id: UUID = Form(...),
    mri_image: UploadFile = File(...),
) -> PredictionResult | PredictionRead:
    """
    Upload ảnh MRI và chạy dự đoán u não.

    Backend sẽ:
    - kiểm tra bệnh nhân tồn tại,
    - lưu ảnh MRI vào storage,
    - chạy model EfficientNetB0 best_tl_model.h5,
    - tạo Grad-CAM,
    - lưu lịch sử dự đoán vào database.
    """

    patient = PatientService(db).get_by_id(
        patient_id,
        current_user=current_user,
    )

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Kết thúc read transaction trước khi chạy TensorFlow/Grad-CAM để không giữ
    # database connection trong suốt tác vụ CPU nặng.
    db.commit()

    try:
        prediction = PredictionService(db).create_prediction(
            patient=patient,
            doctor=current_user,
            upload_file=mri_image,
        )
        AuditService(db).log_request(
            request=request,
            action=AuditAction.create_prediction,
            actor=current_user,
            entity_type="prediction",
            entity_id=prediction.id,
            metadata={
                "patient_id": str(prediction.patient_id),
                "status": prediction.status.value,
                "predicted_class": (
                    prediction.predicted_class.value
                    if prediction.predicted_class
                    else None
                ),
                "confidence": prediction.confidence,
            },
        )
        db.commit()
        db.refresh(prediction)
    except ValueError as exc:
        # Lỗi người dùng: file sai định dạng, quá dung lượng, path không hợp lệ...
        db.rollback()
        AuditService(db).log_request(
            request=request,
            action=AuditAction.create_prediction_failed,
            actor=current_user,
            entity_type="patient",
            entity_id=patient.id,
            metadata={"failure_type": "invalid_upload"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        # Lỗi hệ thống không trả chi tiết kỹ thuật ra frontend.
        db.rollback()
        AuditService(db).log_request(
            request=request,
            action=AuditAction.create_prediction_failed,
            actor=current_user,
            entity_type="patient",
            entity_id=patient.id,
            metadata={"failure_type": "system_error"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction request failed",
        ) from exc

    if prediction.status == PredictionStatus.failed:
        return PredictionRead.model_validate(prediction)

    if (
        prediction.predicted_class is None
        or prediction.confidence is None
        or prediction.probabilities is None
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction succeeded but result data is incomplete",
        )

    return PredictionResult(
        prediction_id=prediction.id,
        patient_id=prediction.patient_id,
        predicted_class=prediction.predicted_class,
        confidence=prediction.confidence,
        probabilities=prediction.probabilities,
        mri_image_path=prediction.mri_image_path,
        gradcam_image_path=prediction.gradcam_image_path,
        expires_at=prediction.expires_at,
    )


@router.get(
    "",
    response_model=PaginatedResponse[PredictionDetail],
    status_code=status.HTTP_200_OK,
)
def list_predictions(
    db: DbSession,
    current_user: DoctorOrAdminUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    patient_id: UUID | None = Query(default=None),
    doctor_id: UUID | None = Query(default=None),
    predicted_class: TumorClass | None = Query(default=None),
    prediction_status: PredictionStatus | None = Query(default=None),
) -> PaginatedResponse[PredictionDetail]:
    """
    Xem lịch sử dự đoán có phân trang và bộ lọc.
    """

    pagination = PaginationParams(page=page, page_size=page_size)
    filters = PredictionFilter(
        patient_id=patient_id,
        doctor_id=doctor_id,
        predicted_class=predicted_class,
        status=prediction_status,
    )

    result = PredictionService(db).list_predictions(
        current_user=current_user,
        pagination=pagination,
        filters=filters,
    )

    return PaginatedResponse[PredictionDetail].create(
        items=[
            PredictionDetail.model_validate(prediction)
            for prediction in result.items
        ],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.post(
    "/cleanup-expired-files",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
def cleanup_expired_files(
    request: Request,
    db: DbSession,
    current_admin: AdminUser,
) -> MessageResponse:
    """
    Admin xóa MRI/Grad-CAM đã hết hạn khỏi storage.

    Chỉ xóa file vật lý, không xóa record lịch sử trong database.
    """

    deleted_count = PredictionService(db).delete_expired_files()
    AuditService(db).log_request(
        request=request,
        action=AuditAction.delete_expired_files,
        actor=current_admin,
        entity_type="prediction_files",
        metadata={"deleted_count": deleted_count},
    )
    db.commit()

    return MessageResponse(
        message=f"Cleaned files for {deleted_count} expired prediction(s)"
    )


@router.get(
    "/{prediction_id}",
    response_model=PredictionDetail,
    status_code=status.HTTP_200_OK,
)
def get_prediction(
    prediction_id: UUID,
    request: Request,
    db: DbSession,
    current_user: DoctorOrAdminUser,
) -> PredictionDetail:
    """
    Xem chi tiết một lần dự đoán.
    """

    prediction = PredictionService(db).get_detail_by_id(
        prediction_id,
        current_user=current_user,
    )

    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found",
        )

    AuditService(db).log_request(
        request=request,
        action=AuditAction.view_prediction,
        actor=current_user,
        entity_type="prediction",
        entity_id=prediction.id,
        metadata={"patient_id": str(prediction.patient_id)},
    )
    db.commit()

    return PredictionDetail.model_validate(prediction)
