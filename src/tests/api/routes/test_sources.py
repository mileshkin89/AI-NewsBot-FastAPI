"""Tests for Sources API routes."""

import pytest
from fastapi.testclient import TestClient

from database.enams import SourceType


@pytest.mark.asyncio
async def test_create_source(client: TestClient) -> None:
    """Create a new source and assert response shape and status."""
    payload = {
        "name": "Example Source",
        "type": SourceType.SITE.value,
        "url": "https://example.com/feed",
        "title_selector": ".title",
        "enabled": True,
    }
    response = client.post("/sources", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Example Source"
    assert data["type"] == SourceType.SITE.value
    assert data["url"] == "https://example.com/feed"
    assert data["title_selector"] == ".title"
    assert data["enabled"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_list_sources_empty(client: TestClient) -> None:
    """List sources returns empty list and pagination when no sources exist."""
    response = client.get("/sources")
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert data["sources"] == []
    assert data["pagination"]["total"] == 0
    assert data["pagination"]["has_more"] is False


@pytest.mark.asyncio
async def test_list_sources_with_data(client: TestClient, source) -> None:
    """List sources returns created source and correct pagination."""
    response = client.get("/sources")
    assert response.status_code == 200
    data = response.json()
    assert len(data["sources"]) == 1
    assert data["sources"][0]["id"] == source.id
    assert data["sources"][0]["name"] == "Test Source"
    assert data["sources"][0]["type"] == SourceType.SITE.value
    assert data["pagination"]["total"] == 1


@pytest.mark.asyncio
async def test_list_sources_filter_enabled(client: TestClient, source) -> None:
    """List sources with enabled filter returns only matching sources."""
    response = client.get("/sources?enabled=true")
    assert response.status_code == 200
    assert len(response.json()["sources"]) == 1
    response_false = client.get("/sources?enabled=false")
    assert response_false.status_code == 200
    assert len(response_false.json()["sources"]) == 0


@pytest.mark.asyncio
async def test_get_source_success(client: TestClient, source) -> None:
    """Get source by id returns source when it exists."""
    response = client.get(f"/sources/{source.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == source.id
    assert data["name"] == "Test Source"
    assert data["type"] == SourceType.SITE.value
    assert data["enabled"] is True


@pytest.mark.asyncio
async def test_get_source_not_found(client: TestClient) -> None:
    """Get source by id returns 404 when source does not exist."""
    response = client.get("/sources/99999")
    assert response.status_code == 404
    assert response.json().get("detail") == "Source not found"


@pytest.mark.asyncio
async def test_get_categories_by_source(client: TestClient, source) -> None:
    """List categories by source returns paginated categories (empty when none assigned)."""
    response = client.get(f"/source/{source.id}/categories")
    assert response.status_code == 200
    data = response.json()
    assert data["source"]["id"] == source.id
    assert "categories" in data
    assert data["categories"] == []
    assert "pagination" in data


@pytest.mark.asyncio
async def test_update_source_success(client: TestClient, source) -> None:
    """Update source with partial data updates only provided fields."""
    payload = {"name": "Updated Source Name", "enabled": False}
    response = client.put(f"/sources/{source.id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Source Name"
    assert data["enabled"] is False
    assert data["id"] == source.id


@pytest.mark.asyncio
async def test_update_source_not_found(client: TestClient) -> None:
    """Update source returns 404 when source does not exist."""
    response = client.put("/sources/99999", json={"name": "x"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deactivate_source(client: TestClient, source) -> None:
    """Deactivate source sets enabled to false."""
    assert source.enabled is True
    response = client.patch(f"/sources/{source.id}/deactivate")
    assert response.status_code == 200
    assert response.json()["enabled"] is False


@pytest.mark.asyncio
async def test_activate_source(client: TestClient, source) -> None:
    """Activate source sets enabled to true."""
    response = client.patch(f"/sources/{source.id}/activate")
    assert response.status_code == 200
    assert response.json()["enabled"] is True


@pytest.mark.asyncio
async def test_delete_source_success(client: TestClient, source) -> None:
    """Delete source returns 204 and removes the source."""
    response = client.delete(f"/sources/{source.id}")
    assert response.status_code == 204
    get_response = client.get(f"/sources/{source.id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_source_not_found(client: TestClient) -> None:
    """Delete source returns 404 when source does not exist."""
    response = client.delete("/sources/99999")
    assert response.status_code == 404
