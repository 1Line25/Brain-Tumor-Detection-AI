from datetime import datetime, timedelta, timezone

from app.models.patient import Patient
from app.models.prediction import Prediction, PredictionStatus
from app.models.user import User, UserRole
from app.schemas.common import PaginationParams
from app.services.patient_service import PatientService
from app.services.prediction_service import PredictionService


def create_user(db_session, *, username: str, role: UserRole) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        password_hash="test-password-hash",
        full_name=f"Test {username}",
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


def create_patient(
    db_session,
    *,
    patient_code: str,
    doctor: User,
) -> Patient:
    patient = Patient(
        patient_code=patient_code,
        full_name=f"Patient {patient_code}",
        created_by=doctor.id,
    )
    db_session.add(patient)
    db_session.flush()
    return patient


def create_prediction(
    db_session,
    *,
    patient: Patient,
    doctor: User,
) -> Prediction:
    prediction = Prediction(
        patient_id=patient.id,
        doctor_id=doctor.id,
        mri_image_path=f"storage/mri/{patient.patient_code}.png",
        gradcam_image_path=None,
        status=PredictionStatus.failed,
        error_message="test",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        files_deleted=False,
    )
    db_session.add(prediction)
    db_session.flush()
    return prediction


def test_doctor_only_lists_own_patients(db_session):
    doctor_a = create_user(
        db_session,
        username="doctor_a",
        role=UserRole.doctor,
    )
    doctor_b = create_user(
        db_session,
        username="doctor_b",
        role=UserRole.doctor,
    )
    own_patient = create_patient(
        db_session,
        patient_code="OWN001",
        doctor=doctor_a,
    )
    create_patient(
        db_session,
        patient_code="OTHER001",
        doctor=doctor_b,
    )

    result = PatientService(db_session).list_patients(
        current_user=doctor_a,
        pagination=PaginationParams(page=1, page_size=20),
    )

    assert [patient.id for patient in result.items] == [own_patient.id]
    assert result.total == 1


def test_doctor_cannot_get_another_doctors_patient(db_session):
    doctor_a = create_user(
        db_session,
        username="doctor_c",
        role=UserRole.doctor,
    )
    doctor_b = create_user(
        db_session,
        username="doctor_d",
        role=UserRole.doctor,
    )
    other_patient = create_patient(
        db_session,
        patient_code="OTHER002",
        doctor=doctor_b,
    )

    patient = PatientService(db_session).get_by_id(
        other_patient.id,
        current_user=doctor_a,
    )

    assert patient is None


def test_admin_can_get_any_patient(db_session):
    admin = create_user(
        db_session,
        username="admin_access",
        role=UserRole.admin,
    )
    doctor = create_user(
        db_session,
        username="doctor_e",
        role=UserRole.doctor,
    )
    patient = create_patient(
        db_session,
        patient_code="ADMIN001",
        doctor=doctor,
    )

    result = PatientService(db_session).get_by_id(
        patient.id,
        current_user=admin,
    )

    assert result is not None
    assert result.id == patient.id


def test_doctor_only_lists_own_predictions(db_session):
    doctor_a = create_user(
        db_session,
        username="doctor_f",
        role=UserRole.doctor,
    )
    doctor_b = create_user(
        db_session,
        username="doctor_g",
        role=UserRole.doctor,
    )
    patient_a = create_patient(
        db_session,
        patient_code="PRED001",
        doctor=doctor_a,
    )
    patient_b = create_patient(
        db_session,
        patient_code="PRED002",
        doctor=doctor_b,
    )
    own_prediction = create_prediction(
        db_session,
        patient=patient_a,
        doctor=doctor_a,
    )
    create_prediction(
        db_session,
        patient=patient_b,
        doctor=doctor_b,
    )

    result = PredictionService(db_session).list_predictions(
        current_user=doctor_a,
        pagination=PaginationParams(page=1, page_size=20),
    )

    assert [prediction.id for prediction in result.items] == [
        own_prediction.id
    ]
    assert result.total == 1


def test_doctor_cannot_get_another_doctors_prediction(db_session):
    doctor_a = create_user(
        db_session,
        username="doctor_h",
        role=UserRole.doctor,
    )
    doctor_b = create_user(
        db_session,
        username="doctor_i",
        role=UserRole.doctor,
    )
    patient_b = create_patient(
        db_session,
        patient_code="PRED003",
        doctor=doctor_b,
    )
    other_prediction = create_prediction(
        db_session,
        patient=patient_b,
        doctor=doctor_b,
    )

    result = PredictionService(db_session).get_detail_by_id(
        other_prediction.id,
        current_user=doctor_a,
    )

    assert result is None
