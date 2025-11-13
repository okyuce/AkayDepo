"""
Auth API Tests
"""
from fastapi.testclient import TestClient


def test_login_success(client: TestClient):
    """Test successful login"""
    response = client.post(
        "/v1/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client: TestClient):
    """Test login with invalid credentials"""
    response = client.post(
        "/v1/auth/login",
        json={"username": "admin", "password": "wrongpassword"}
    )
    assert response.status_code == 401


def test_get_me(client: TestClient, auth_headers: dict):
    """Test get current user"""
    response = client.get("/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"


def test_protected_endpoint_without_token(client: TestClient):
    """Test protected endpoint without token"""
    response = client.get("/v1/auth/me")
    assert response.status_code == 403  # No credentials provided
