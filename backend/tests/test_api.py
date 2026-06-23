import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    # Even if database is not set up correctly in test environment, we expect a 200 OK
    # and either 'ok' or 'degraded' status
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["ok", "degraded"]
    assert "app" in data

@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "wronguser", "password": "wrongpassword"}
    )
    # The system should return 401 Unauthorized or 404/400 depending on implementation
    # Assuming standard FastAPI behavior for unauthorized
    assert response.status_code in [401, 404, 400]

@pytest.mark.asyncio
async def test_get_patients_unauthorized(client: AsyncClient):
    # Trying to access protected route without token
    response = await client.get("/api/v1/patients")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
