"""Tests for Users API routes."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_list_users_empty(client: TestClient) -> None:
    """List users returns empty list and pagination when no users exist."""
    response = client.get("/users")
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert data["users"] == []
    assert data["pagination"]["total"] == 0
    assert data["pagination"]["has_more"] is False


@pytest.mark.asyncio
async def test_list_users_with_data(client: TestClient, user) -> None:
    """List users returns created user and correct pagination."""
    response = client.get("/users")
    assert response.status_code == 200
    data = response.json()
    assert len(data["users"]) == 1
    assert data["users"][0]["id"] == user.id
    assert data["users"][0]["chat_id"] == 123456789
    assert data["users"][0]["active"] is True
    assert "subscribed_at" in data["users"][0]
    assert data["pagination"]["total"] == 1


@pytest.mark.asyncio
async def test_list_users_filter_active(client: TestClient, user) -> None:
    """List users with active filter returns only matching users."""
    response = client.get("/users?active=true")
    assert response.status_code == 200
    assert len(response.json()["users"]) == 1
    response_false = client.get("/users?active=false")
    assert response_false.status_code == 200
    assert len(response_false.json()["users"]) == 0


@pytest.mark.asyncio
async def test_list_users_sort_invalid(client: TestClient) -> None:
    """List users returns 400 when sort_by is invalid."""
    response = client.get("/users?sort_by=invalid_field")
    assert response.status_code == 400
    assert "Cannot sort by" in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_get_user_success(client: TestClient, user) -> None:
    """Get user by id returns user when it exists."""
    response = client.get(f"/users/{user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user.id
    assert data["chat_id"] == 123456789
    assert data["active"] is True
    assert "subscribed_at" in data


@pytest.mark.asyncio
async def test_get_user_not_found(client: TestClient) -> None:
    """Get user by id returns 404 when user does not exist."""
    response = client.get("/users/99999")
    assert response.status_code == 404
    assert response.json().get("detail") == "User not found"


@pytest.mark.asyncio
async def test_get_categories_by_user(client: TestClient, user) -> None:
    """List categories by user returns paginated categories (empty when none subscribed)."""
    response = client.get(f"/users/{user.id}/categories")
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["id"] == user.id
    assert "categories" in data
    assert data["categories"] == []
    assert "pagination" in data


@pytest.mark.asyncio
async def test_deactivate_user(client: TestClient, user) -> None:
    """Deactivate user sets active to false."""
    assert user.active is True
    response = client.patch(f"/users/{user.id}/deactivate")
    assert response.status_code == 200
    assert response.json()["active"] is False


@pytest.mark.asyncio
async def test_activate_user(client: TestClient, user) -> None:
    """Activate user sets active to true."""
    response = client.patch(f"/users/{user.id}/activate")
    assert response.status_code == 200
    assert response.json()["active"] is True


@pytest.mark.asyncio
async def test_delete_user_success(client: TestClient, user) -> None:
    """Delete user returns 204 and removes the user."""
    response = client.delete(f"/users/{user.id}")
    assert response.status_code == 204
    get_response = client.get(f"/users/{user.id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_not_found(client: TestClient) -> None:
    """Delete user returns 404 when user does not exist."""
    response = client.delete("/users/99999")
    assert response.status_code == 404
