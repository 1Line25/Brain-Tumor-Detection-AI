import pytest
from sqlalchemy import func, select

from app.models.login_throttle import LoginThrottle
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest
from app.services.auth_service import AuthService, LoginRateLimitError


def create_user(db_session, *, username: str) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        password_hash="test-password-hash",
        full_name=f"Test {username}",
        role=UserRole.doctor,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_account_is_locked_after_repeated_failures(
    db_session,
    monkeypatch,
):
    user = create_user(db_session, username="lockout_doctor")
    monkeypatch.setattr(
        "app.services.auth_service.verify_password",
        lambda *_: False,
    )
    request = LoginRequest(
        identifier=user.username,
        password="wrong-password",
    )

    for _ in range(4):
        with pytest.raises(ValueError):
            AuthService(db_session).login(
                request,
                client_ip="192.0.2.10",
            )
        db_session.commit()

    with pytest.raises(LoginRateLimitError) as exc_info:
        AuthService(db_session).login(
            request,
            client_ip="192.0.2.10",
        )
    db_session.commit()

    assert exc_info.value.retry_after_seconds > 0

    with pytest.raises(LoginRateLimitError):
        AuthService(db_session).login(
            request,
            client_ip="192.0.2.11",
        )


def test_successful_login_clears_failure_counters(
    db_session,
    monkeypatch,
):
    user = create_user(db_session, username="reset_throttle_doctor")
    password_is_valid = False

    def fake_verify_password(*_):
        return password_is_valid

    monkeypatch.setattr(
        "app.services.auth_service.verify_password",
        fake_verify_password,
    )
    request = LoginRequest(
        identifier=user.username,
        password="password-value",
    )

    for _ in range(2):
        with pytest.raises(ValueError):
            AuthService(db_session).login(
                request,
                client_ip="192.0.2.20",
            )
        db_session.commit()

    password_is_valid = True
    service = AuthService(db_session)
    account_key = service.login_throttle_service.build_account_key(
        user_id=str(user.id),
        identifier=user.username,
    )
    ip_key = service.login_throttle_service.build_ip_key("192.0.2.20")
    response = service.login(
        request,
        client_ip="192.0.2.20",
    )
    db_session.commit()

    assert response.user.id == user.id
    remaining = db_session.scalar(
        select(func.count())
        .select_from(LoginThrottle)
        .where(
            LoginThrottle.scope_key.in_([account_key, ip_key])
        )
    )
    assert remaining == 0


@pytest.mark.asyncio
async def test_login_endpoint_returns_429_and_retry_after(client):
    payload = {
        "identifier": "unknown-rate-limited-user",
        "password": "wrong-password",
    }

    for _ in range(4):
        response = await client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401

    response = await client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0
