import pytest

from app.api.deps import get_current_user
from app.main import app
from app.models.user import User, UserRole


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
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_admin_can_list_all_users(client, db_session):
    admin = create_user(
        db_session,
        username="admin_list_users",
        role=UserRole.admin,
    )
    doctor = create_user(
        db_session,
        username="doctor_visible_to_admin",
        role=UserRole.doctor,
    )
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        response = await client.get(
            "/api/v1/users?page=1&page_size=100"
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    usernames = {item["username"] for item in response.json()["items"]}
    assert admin.username in usernames
    assert doctor.username in usernames


@pytest.mark.asyncio
async def test_doctor_cannot_list_users(client, db_session):
    doctor = create_user(
        db_session,
        username="doctor_cannot_list_users",
        role=UserRole.doctor,
    )
    app.dependency_overrides[get_current_user] = lambda: doctor

    try:
        response = await client.get("/api/v1/users")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin permission is required"
