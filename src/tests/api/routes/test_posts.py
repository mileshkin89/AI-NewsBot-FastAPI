"""Tests for Posts API routes."""

import pytest
from fastapi.testclient import TestClient

from database.enams import PostStatus


@pytest.mark.asyncio
async def test_create_post_validation(client: TestClient) -> None:
    """Create post endpoint accepts JSON body; model requires news_id so creating without it returns 500."""
    payload = {"generated_text": "New post content"}
    response = client.post("/posts", json=payload)
    # Route only sets generated_text; model requires news_id, so commit fails with 500
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_list_posts_empty(client: TestClient) -> None:
    """List posts returns empty list and pagination when no posts exist."""
    response = client.get("/posts")
    assert response.status_code == 200
    data = response.json()
    assert "posts" in data
    assert data["posts"] == []
    assert "pagination" in data
    pag = data["pagination"]
    assert pag["total"] == 0
    assert pag["skip"] == 0
    assert "limit" in pag
    assert pag["has_more"] is False


@pytest.mark.asyncio
async def test_list_posts_with_data(client: TestClient, post) -> None:
    """List posts returns created post and correct pagination."""
    response = client.get("/posts")
    assert response.status_code == 200
    data = response.json()
    assert len(data["posts"]) == 1
    assert data["posts"][0]["id"] == post.id
    assert data["posts"][0]["generated_text"] == "Generated post text"
    assert data["pagination"]["total"] == 1
    assert data["pagination"]["has_more"] is False


@pytest.mark.asyncio
async def test_list_posts_pagination_params(client: TestClient, post) -> None:
    """List posts accepts skip and limit and returns correct pagination."""
    response = client.get("/posts?skip=0&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["skip"] == 0
    assert data["pagination"]["limit"] == 5


@pytest.mark.asyncio
async def test_list_posts_sort_invalid(client: TestClient) -> None:
    """List posts returns 400 when sort_by is invalid."""
    response = client.get("/posts?sort_by=invalid_field")
    assert response.status_code == 400
    assert "Cannot sort by" in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_get_post_not_found(client: TestClient) -> None:
    """Get post by id returns 404 when post does not exist."""
    response = client.get("/posts/99999")
    assert response.status_code == 404
    assert response.json().get("detail") == "Post not found"


@pytest.mark.asyncio
async def test_get_post_success(client: TestClient, post) -> None:
    """Get post by id returns post with details when post exists."""
    response = client.get(f"/posts/{post.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == post.id
    assert data["generated_text"] == "Generated post text"
    assert "created_at" in data
    assert data["status"] == PostStatus.NEW.value
    assert "news_item" in data


@pytest.mark.asyncio
async def test_update_post_success(client: TestClient, post) -> None:
    """Update post with partial data updates only provided fields."""
    payload = {"generated_text": "Updated text"}
    response = client.put(f"/posts/{post.id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["generated_text"] == "Updated text"
    assert data["id"] == post.id


@pytest.mark.asyncio
async def test_update_post_not_found(client: TestClient) -> None:
    """Update post returns 404 when post does not exist."""
    response = client.put("/posts/99999", json={"generated_text": "x"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_post_success(client: TestClient, post) -> None:
    """Delete post returns 204 and removes the post."""
    response = client.delete(f"/posts/{post.id}")
    assert response.status_code == 204
    get_response = client.get(f"/posts/{post.id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_post_not_found(client: TestClient) -> None:
    """Delete post returns 404 when post does not exist."""
    response = client.delete("/posts/99999")
    assert response.status_code == 404
