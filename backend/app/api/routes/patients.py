from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession, DoctorOrAdminUser
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.patient import (
    PatientCreate,
    PatientDetail,
    PatientRead,
    PatientUpdate,
)
from app.services.patient_service import PatientService


router = APIRouter(
    prefix="/patients",
    tags=["Patients"],
)


@router.post(
    "",
    response_model=PatientRead,
    status_code=status.HTTP_201_CREATED,
)
def create_patient(
    data: PatientCreate,
    db: DbSession,
    current_user: DoctorOrAdminUser,
) -> PatientRead:
    """
    Tạo hồ sơ bệnh nhân mới.

    created_by không lấy từ frontend. Backend tự lấy từ user đang đăng nhập
    để tránh giả mạo bác sĩ/người tạo hồ sơ.
    """

    try:
        patient = PatientService(db).create(
            data=data,
            created_by_user=current_user,
        )
        db.commit()
        db.refresh(patient)
        return PatientRead.model_validate(patient)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=PaginatedResponse[PatientRead],
    status_code=status.HTTP_200_OK,
)
def list_patients(
    db: DbSession,
    _: DoctorOrAdminUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    created_by: UUID | None = Query(default=None),
) -> PaginatedResponse[PatientRead]:
    """
    Lấy danh sách bệnh nhân có phân trang.

    keyword tìm theo:
    - mã bệnh nhân,
    - họ tên,
    - số điện thoại.
    """

    pagination = PaginationParams(page=page, page_size=page_size)

    result = PatientService(db).list_patients(
        pagination=pagination,
        keyword=keyword,
        created_by=created_by,
    )

    return PaginatedResponse[PatientRead].create(
        items=[PatientRead.model_validate(patient) for patient in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get(
    "/{patient_id}",
    response_model=PatientDetail,
    status_code=status.HTTP_200_OK,
)
def get_patient(
    patient_id: UUID,
    db: DbSession,
    _: DoctorOrAdminUser,
) -> PatientDetail:
    """
    Xem chi tiết hồ sơ bệnh nhân.

    Response có kèm thông tin user đã tạo hồ sơ.
    """

    patient = PatientService(db).get_detail_by_id(patient_id)

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    return PatientDetail.model_validate(patient)


@router.patch(
    "/{patient_id}",
    response_model=PatientRead,
    status_code=status.HTTP_200_OK,
)
def update_patient(
    patient_id: UUID,
    data: PatientUpdate,
    db: DbSession,
    _: DoctorOrAdminUser,
) -> PatientRead:
    """
    Cập nhật thông tin bệnh nhân.

    Không cho đổi patient_code ở endpoint này để giữ mã bệnh nhân ổn định.
    """

    service = PatientService(db)
    patient = service.get_by_id(patient_id)

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    updated_patient = service.update(
        patient=patient,
        data=data,
    )
    db.commit()
    db.refresh(updated_patient)

    return PatientRead.model_validate(updated_patient)
