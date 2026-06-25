from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.api.deps import DbSession, DoctorOrAdminUser
from app.models.audit_log import AuditAction
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.patient import (
    PatientCreate,
    PatientDetail,
    PatientDuplicateCheck,
    PatientDuplicateResult,
    PatientRead,
    PatientUpdate,
)
from app.services.patient_service import PatientService
from app.services.audit_service import AuditService


router = APIRouter(
    prefix="/patients",
    tags=["Patients"],
)


@router.post(
    "/duplicate-check",
    response_model=PatientDuplicateResult,
    status_code=status.HTTP_200_OK,
)
def check_patient_duplicates(
    data: PatientDuplicateCheck,
    db: DbSession,
    current_user: DoctorOrAdminUser,
) -> PatientDuplicateResult:
    """Cảnh báo các hồ sơ có cùng số điện thoại hoặc cùng tên/ngày sinh."""

    matches = PatientService(db).find_possible_duplicates(
        data=data,
        current_user=current_user,
    )
    return PatientDuplicateResult(
        possible_duplicates=[
            PatientRead.model_validate(patient)
            for patient in matches
        ],
    )


@router.post(
    "",
    response_model=PatientRead,
    status_code=status.HTTP_201_CREATED,
)
def create_patient(
    data: PatientCreate,
    request: Request,
    db: DbSession,
    current_user: DoctorOrAdminUser,
) -> PatientRead:
    """
    Tạo hồ sơ bệnh nhân mới.

    Database tự sinh patient_code duy nhất. created_by không lấy từ frontend;
    backend tự lấy từ user đang đăng nhập để tránh giả mạo người tạo hồ sơ.
    """

    try:
        patient = PatientService(db).create(
            data=data,
            created_by_user=current_user,
        )
        AuditService(db).log_request(
            request=request,
            action=AuditAction.create_patient,
            actor=current_user,
            entity_type="patient",
            entity_id=patient.id,
            metadata={"patient_code": patient.patient_code},
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
    current_user: DoctorOrAdminUser,
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
        current_user=current_user,
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
    request: Request,
    db: DbSession,
    current_user: DoctorOrAdminUser,
) -> PatientDetail:
    """
    Xem chi tiết hồ sơ bệnh nhân.

    Response có kèm thông tin user đã tạo hồ sơ.
    """

    patient = PatientService(db).get_detail_by_id(
        patient_id,
        current_user=current_user,
    )

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    AuditService(db).log_request(
        request=request,
        action=AuditAction.view_patient,
        actor=current_user,
        entity_type="patient",
        entity_id=patient.id,
        metadata={"patient_code": patient.patient_code},
    )
    db.commit()

    return PatientDetail.model_validate(patient)


@router.patch(
    "/{patient_id}",
    response_model=PatientRead,
    status_code=status.HTTP_200_OK,
)
def update_patient(
    patient_id: UUID,
    data: PatientUpdate,
    request: Request,
    db: DbSession,
    current_user: DoctorOrAdminUser,
) -> PatientRead:
    """
    Cập nhật thông tin bệnh nhân.

    Không cho đổi patient_code ở endpoint này để giữ mã bệnh nhân ổn định.
    """

    service = PatientService(db)
    patient = service.get_by_id(
        patient_id,
        current_user=current_user,
    )

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    updated_patient = service.update(
        patient=patient,
        data=data,
    )
    AuditService(db).log_request(
        request=request,
        action=AuditAction.update_patient,
        actor=current_user,
        entity_type="patient",
        entity_id=updated_patient.id,
        metadata={
            "patient_code": updated_patient.patient_code,
            "updated_fields": sorted(
                data.model_dump(exclude_unset=True).keys()
            ),
        },
    )
    db.commit()
    db.refresh(updated_patient)

    return PatientRead.model_validate(updated_patient)
