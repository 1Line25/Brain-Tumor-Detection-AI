import pytest
from sqlalchemy import select

from app.api.deps import get_current_user
from app.main import app
from app.models.audit_log import AuditAction, AuditLog
from app.models.user import User, UserRole
from app.services.audit_service import AuditService


def create_user(
    db_session,
    *,
    username: str,
    role: UserRole,
) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        password_hash="test-password-hash",
        full_name=f"Test {username}",
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_failed_login_is_written_to_audit_log(client, db_session):
    response = await client.post(
        "/api/v1/auth/login",
        headers={"X-Real-IP": "198.51.100.41"},
        json={
            "identifier": "audit-unknown-user",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    log = db_session.scalar(
        select(AuditLog)
        .where(
            AuditLog.action == AuditAction.login_failed,
            AuditLog.ip_address == "198.51.100.41",
        )
        .order_by(AuditLog.created_at.desc())
    )
    assert log is not None
    assert log.actor_id is None
    assert log.metadata_json["result"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_create_patient_writes_actor_and_entity(client, db_session):
    doctor = create_user(
        db_session,
        username="audit_patient_doctor",
        role=UserRole.doctor,
    )
    app.dependency_overrides[get_current_user] = lambda: doctor

    try:
        response = await client.post(
            "/api/v1/patients",
            headers={"X-Real-IP": "198.51.100.42"},
            json={
                "patient_code": "AUDIT001",
                "full_name": "Audit Patient",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 201
    patient_id = response.json()["id"]
    log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == AuditAction.create_patient,
            AuditLog.entity_id == patient_id,
        )
    )
    assert log is not None
    assert log.actor_id == doctor.id
    assert log.ip_address == "198.51.100.42"
    assert log.metadata_json["patient_code"] == "AUDIT001"


@pytest.mark.asyncio
async def test_audit_api_returns_actor_details(client, db_session):
    admin = create_user(
        db_session,
        username="audit_view_admin",
        role=UserRole.admin,
    )
    log = AuditService(db_session).log(
        action=AuditAction.update_user,
        actor=admin,
        entity_type="user",
        entity_id=admin.id,
        metadata={"updated_fields": ["full_name"]},
    )
    db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        response = await client.get(
            f"/api/v1/audit-logs?entity_id={admin.id}"
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    item = next(
        item
        for item in response.json()["items"]
        if item["id"] == str(log.id)
    )
    assert item["actor"]["username"] == admin.username


def test_audit_metadata_masks_sensitive_values(db_session):
    log = AuditService(db_session).log(
        action=AuditAction.reset_password,
        metadata={
            "new_password": "secret-value",
            "reason": "admin reset",
        },
    )

    assert log.metadata_json["new_password"] == "***"
    assert log.metadata_json["reason"] == "admin reset"
