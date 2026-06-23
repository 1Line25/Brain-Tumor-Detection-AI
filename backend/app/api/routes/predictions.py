from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.api.deps import AdminUser, DbSession, DoctorOrAdminUser
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


router = APIRouter(
    prefix="/predictions",
    tags=["Predictions"],
)


@router.post(
    "",
    response_model=PredictionResult | PredictionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_prediction(
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
    - chạy model best_cnn_model.h5,
    - tạo Grad-CAM,
    - lưu lịch sử dự đoán vào database.
    """

    patient = PatientService(db).get_by_id(patient_id)

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    try:
        prediction = await PredictionService(db).create_prediction(
            patient=patient,
            doctor=current_user,
            upload_file=mri_image,
        )
        db.commit()
        db.refresh(prediction)
    except ValueError as exc:
        # Lỗi người dùng: file sai định dạng, quá dung lượng, path không hợp lệ...
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        # Lỗi hệ thống không trả chi tiết kỹ thuật ra frontend.
        db.rollback()
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
        gradcam_image_path=prediction.gradcam_image_path,
        expires_at=prediction.expires_at,
    )


@router.get(
    "",
    response_model=PaginatedResponse[PredictionRead],
    status_code=status.HTTP_200_OK,
)
def list_predictions(
    db: DbSession,
    _: DoctorOrAdminUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    patient_id: UUID | None = Query(default=None),
    doctor_id: UUID | None = Query(default=None),
    predicted_class: TumorClass | None = Query(default=None),
    prediction_status: PredictionStatus | None = Query(default=None),
) -> PaginatedResponse[PredictionRead]:
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
        pagination=pagination,
        filters=filters,
    )

    return PaginatedResponse[PredictionRead].create(
        items=[
            PredictionRead.model_validate(prediction)
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
    db: DbSession,
    _: AdminUser,
) -> MessageResponse:
    """
    Admin xóa MRI/Grad-CAM đã hết hạn khỏi storage.

    Chỉ xóa file vật lý, không xóa record lịch sử trong database.
    """

    deleted_count = PredictionService(db).delete_expired_files()
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
    db: DbSession,
    _: DoctorOrAdminUser,
) -> PredictionDetail:
    """
    Xem chi tiết một lần dự đoán.
    """

    prediction = PredictionService(db).get_detail_by_id(prediction_id)

    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found",
        )

    return PredictionDetail.model_validate(prediction)
