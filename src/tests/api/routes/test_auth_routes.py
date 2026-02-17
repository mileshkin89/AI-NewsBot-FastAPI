"""Tests for Auth API routes."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_login_success(client: TestClient, admin_user) -> None:
    """Login with valid email and password returns access token and sets refresh cookie."""
    response = client.post(
        "/auth/token",
        data={"username": admin_user.email, "password": "testpass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data.get("token_type") == "bearer"
    assert "refresh_token" in response.cookies or "Set-Cookie" in [h.lower() for h in response.headers.get_list("set-cookie", [])] or response.headers.get("set-cookie")


@pytest.mark.asyncio
async def test_login_wrong_password(client: TestClient, admin_user) -> None:
    """Login with wrong password returns 401."""
    response = client.post(
        "/auth/token",
        data={"username": admin_user.email, "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert "Incorrect" in response.json().get("detail", "") or response.json().get("detail")


@pytest.mark.asyncio
async def test_login_wrong_username(client: TestClient) -> None:
    """Login with non-existent email returns 401."""
    response = client.post(
        "/auth/token",
        data={"username": "nonexistent@example.com", "password": "anypass123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_without_cookie(client: TestClient) -> None:
    """Refresh token without refresh_token cookie returns 401."""
    response = client.post("/auth/token/refresh")
    assert response.status_code == 401
    assert "refresh" in response.json().get("detail", "").lower() or "cookie" in response.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_refresh_token_success(client: TestClient, admin_user) -> None:
    """Refresh token with valid cookie returns new access token."""
    login_response = client.post(
        "/auth/token",
        data={"username": admin_user.email, "password": "testpass123"},
    )
    assert login_response.status_code == 200
    refresh_token = login_response.cookies.get("refresh_token")
    if not refresh_token:
        cookie_header = login_response.headers.get("set-cookie") or ""
        if "refresh_token=" in cookie_header:
            refresh_token = cookie_header.split("refresh_token=")[-1].split(";")[0]
    assert refresh_token, "Login must set refresh_token cookie"
    client.cookies.set("refresh_token", refresh_token)
    response = client.post("/auth/token/refresh")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data.get("token_type") == "bearer"


@pytest.mark.asyncio
async def test_logout_success(client: TestClient, admin_user) -> None:
    """Logout with valid Bearer token returns 200 and clears session."""
    login_response = client.post(
        "/auth/token",
        data={"username": admin_user.email, "password": "testpass123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    assert response.json().get("message") == "Successfully logged out"


@pytest.mark.asyncio
async def test_logout_unauthorized(client: TestClient) -> None:
    """Logout without token returns 401."""
    response = client.post("/auth/logout")
    assert response.status_code == 401
