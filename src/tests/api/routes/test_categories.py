"""Tests for Categories API routes."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_create_category(client: TestClient) -> None:
    """Create a new category and assert response shape and status."""
    payload = {"name": "Tech News", "enabled": True}
    response = client.post("/categories", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Tech News"
    assert data["enabled"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_list_categories_empty(client: TestClient) -> None:
    """List categories returns empty list and pagination when no categories exist."""
    response = client.get("/categories")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert data["categories"] == []
    assert data["pagination"]["total"] == 0
    assert data["pagination"]["has_more"] is False


@pytest.mark.asyncio
async def test_list_categories_with_data(client: TestClient, category) -> None:
    """List categories returns created category and correct pagination."""
    response = client.get("/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data["categories"]) == 1
    assert data["categories"][0]["id"] == category.id
    assert data["categories"][0]["name"] == "Test Category"
    assert data["categories"][0]["enabled"] is True
    assert data["pagination"]["total"] == 1


@pytest.mark.asyncio
async def test_list_categories_filter_enabled(client: TestClient, category) -> None:
    """List categories with enabled filter returns only matching categories."""
    response = client.get("/categories?enabled=true")
    assert response.status_code == 200
    assert len(response.json()["categories"]) == 1
    response_false = client.get("/categories?enabled=false")
    assert response_false.status_code == 200
    assert len(response_false.json()["categories"]) == 0


@pytest.mark.asyncio
async def test_get_category_success(client: TestClient, category) -> None:
    """Get category by id returns category when it exists."""
    response = client.get(f"/categories/{category.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == category.id
    assert data["name"] == "Test Category"
    assert data["enabled"] is True


@pytest.mark.asyncio
async def test_get_category_not_found(client: TestClient) -> None:
    """Get category by id returns 404 when category does not exist."""
    response = client.get("/categories/99999")
    assert response.status_code == 404
    assert response.json().get("detail") == "Category not found"


@pytest.mark.asyncio
async def test_get_sources_by_category(client: TestClient, category) -> None:
    """List sources by category returns paginated sources (empty when none assigned)."""
    response = client.get(f"/categories/{category.id}/sources")
    assert response.status_code == 200
    data = response.json()
    assert data["category"]["id"] == category.id
    assert "sources" in data
    assert data["sources"] == []
    assert "pagination" in data


@pytest.mark.asyncio
async def test_get_users_by_category(client: TestClient, category) -> None:
    """List users by category returns paginated users (empty when none subscribed)."""
    response = client.get(f"/categories/{category.id}/users")
    assert response.status_code == 200
    data = response.json()
    assert data["category"]["id"] == category.id
    assert "users" in data
    assert "pagination" in data


@pytest.mark.asyncio
async def test_update_category_success(client: TestClient, category) -> None:
    """Update category with partial data updates only provided fields."""
    payload = {"name": "Updated Name", "enabled": False}
    response = client.put(f"/categories/{category.id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["enabled"] is False
    assert data["id"] == category.id


@pytest.mark.asyncio
async def test_update_category_not_found(client: TestClient) -> None:
    """Update category returns 404 when category does not exist."""
    response = client.put("/categories/99999", json={"name": "x"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deactivate_category(client: TestClient, category) -> None:
    """Deactivate category sets enabled to false."""
    assert category.enabled is True
    response = client.patch(f"/categories/{category.id}/deactivate")
    assert response.status_code == 200
    assert response.json()["enabled"] is False


@pytest.mark.asyncio
async def test_activate_category(client: TestClient, category) -> None:
    """Activate category sets enabled to true."""
    response = client.patch(f"/categories/{category.id}/activate")
    assert response.status_code == 200
    assert response.json()["enabled"] is True


@pytest.mark.asyncio
async def test_delete_category_success(client: TestClient, category) -> None:
    """Delete category returns 204 and removes the category."""
    response = client.delete(f"/categories/{category.id}")
    assert response.status_code == 204
    get_response = client.get(f"/categories/{category.id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_category_not_found(client: TestClient) -> None:
    """Delete category returns 404 when category does not exist."""
    response = client.delete("/categories/99999")
    assert response.status_code == 404
