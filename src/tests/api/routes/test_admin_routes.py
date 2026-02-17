"""Tests for Admin API routes."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_list_admins_empty(client: TestClient) -> None:
    """List admins returns empty list when no admins exist in DB."""
    response = client.get("/admins")
    assert response.status_code == 200
    data = response.json()
    assert "admins" in data
    assert data["admins"] == []


@pytest.mark.asyncio
async def test_list_admins_with_data(client: TestClient, admin_user) -> None:
    """List admins returns created admin in the list."""
    response = client.get("/admins")
    assert response.status_code == 200
    data = response.json()
    assert len(data["admins"]) == 1
    assert data["admins"][0]["email"] == "admin@auth-test.example.com"
    assert data["admins"][0]["name"] == "Auth Test Admin"
    assert data["admins"][0]["is_active"] is True
    assert "id" in data["admins"][0]


@pytest.mark.asyncio
async def test_create_admin_success(client: TestClient) -> None:
    """Create admin with valid data returns 201 and admin representation."""
    payload = {
        "email": "newadmin@test.example",
        "name": "New Admin",
        "password": "securepass123",
    }
    response = client.post("/admins", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newadmin@test.example"
    assert data["name"] == "New Admin"
    assert data["is_active"] is True
    assert "id" in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_create_admin_duplicate_email(client: TestClient, admin_user) -> None:
    """Create admin with existing email returns 400 (or 422 if validation fails first)."""
    payload = {
        "email": "admin@auth-test.example.com",
        "name": "Duplicate",
        "password": "pass12345",
    }
    response = client.post("/admins", json=payload)
    assert response.status_code in (400, 422)
    if response.status_code == 400:
        assert response.json().get("detail") == "Admin already exists"


@pytest.mark.asyncio
async def test_deactivate_admin_success(client: TestClient, admin_user) -> None:
    """Deactivate admin returns 200."""
    response = client.patch(f"/admins/{admin_user.id}/deactivate")
    assert response.status_code == 200
    list_response = client.get("/admins")
    assert list_response.status_code == 200
    admins = list_response.json()["admins"]
    found = next((a for a in admins if a["id"] == admin_user.id), None)
    assert found is not None
    assert found["is_active"] is False


@pytest.mark.asyncio
async def test_deactivate_superadmin_forbidden(client: TestClient, superadmin_user) -> None:
    """Deactivate superadmin returns 400 (super admin cannot be deactivated)."""
    response = client.patch(f"/admins/{superadmin_user.id}/deactivate")
    assert response.status_code == 400
    assert "Super admin" in response.json().get("detail", "").lower() or "cannot be deactivated" in response.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_deactivate_admin_not_found(client: TestClient) -> None:
    """Deactivate admin returns 404 when admin does not exist."""
    response = client.patch("/admins/99999/deactivate")
    assert response.status_code == 404
    assert response.json().get("detail") == "Admin not found"


@pytest.mark.asyncio
async def test_activate_admin_success(client: TestClient, admin_user) -> None:
    """Activate admin endpoint returns 200 for existing admin."""
    # First deactivate
    client.patch(f"/admins/{admin_user.id}/deactivate")
    response = client.patch(f"/admins/{admin_user.id}/activate")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_activate_admin_not_found(client: TestClient) -> None:
    """Activate admin returns 404 when admin does not exist."""
    response = client.patch("/admins/99999/activate")
    assert response.status_code == 404
    assert response.json().get("detail") == "Admin not found"
