import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from database.models import Category, Post, Source, User, Admin
from database.db import get_db_depends
from apps.api.apps_api.dependencies import (
    get_category_by_id,
    get_post_by_id,
    get_post_by_id_with_details,
    get_source_by_id,
    get_user_by_id as get_telegram_user_by_id,
)
from apps.api.auth.dependencies import (
    admin_or_superadmin_required,
    admin_required,
    authenticate_user,
    get_current_user,
    get_user_by_email,
    get_user_by_id as get_admin_by_id,
    superadmin_required,
)


@pytest.mark.asyncio
async def test_get_category_by_id_returns_category(
        db_session: AsyncSession, category: Category
) -> None:
    """get_category_by_id returns the category when it exists."""
    result = await get_category_by_id(category_id=category.id, db=db_session)
    assert result is category
    assert result.id == category.id
    assert result.name == category.name


@pytest.mark.asyncio
async def test_get_category_by_id_raises_404_when_not_found(
        db_session: AsyncSession,
) -> None:
    """get_category_by_id raises 404 when category does not exist."""
    with pytest.raises(HTTPException) as exc_info:
        await get_category_by_id(category_id=99999, db=db_session)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Category not found"


@pytest.mark.asyncio
async def test_get_source_by_id_returns_source(
        db_session: AsyncSession, source: Source
) -> None:
    """get_source_by_id returns the source when it exists."""
    result = await get_source_by_id(source_id=source.id, db=db_session)
    assert result is source
    assert result.id == source.id
    assert result.name == source.name


@pytest.mark.asyncio
async def test_get_source_by_id_raises_404_when_not_found(
        db_session: AsyncSession,
) -> None:
    """get_source_by_id raises 404 when source does not exist."""
    with pytest.raises(HTTPException) as exc_info:
        await get_source_by_id(source_id=99999, db=db_session)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Source not found"


@pytest.mark.asyncio
async def test_get_post_by_id_returns_post(
        db_session: AsyncSession, post: Post
) -> None:
    """get_post_by_id returns the post when it exists."""
    result = await get_post_by_id(post_id=post.id, db=db_session)
    assert result is post
    assert result.id == post.id
    assert result.generated_text == post.generated_text


@pytest.mark.asyncio
async def test_get_post_by_id_raises_404_when_not_found(
        db_session: AsyncSession,
) -> None:
    """get_post_by_id raises 404 when post does not exist."""
    with pytest.raises(HTTPException) as exc_info:
        await get_post_by_id(post_id=99999, db=db_session)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Post not found"


@pytest.mark.asyncio
async def test_get_post_by_id_with_details_returns_post_with_relations(
        db_session: AsyncSession, post: Post
) -> None:
    """get_post_by_id_with_details returns post with news, source and categories loaded."""
    result = await get_post_by_id_with_details(post_id=post.id, db=db_session)
    assert result.id == post.id
    assert result.news is not None
    assert result.news.source is not None
    assert hasattr(result.news.source, "categories")


@pytest.mark.asyncio
async def test_get_post_by_id_with_details_raises_404_when_not_found(
        db_session: AsyncSession,
) -> None:
    """get_post_by_id_with_details raises 404 when post does not exist."""
    with pytest.raises(HTTPException) as exc_info:
        await get_post_by_id_with_details(post_id=99999, db=db_session)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Post not found"


@pytest.mark.asyncio
async def test_get_user_by_id_returns_user(
        db_session: AsyncSession, user: User
) -> None:
    """get_user_by_id (Telegram user) returns the user when it exists."""
    result = await get_telegram_user_by_id(user_id=user.id, db=db_session)
    assert result is user
    assert result.id == user.id
    assert result.chat_id == user.chat_id


@pytest.mark.asyncio
async def test_get_user_by_id_raises_404_when_not_found(
        db_session: AsyncSession,
) -> None:
    """get_user_by_id (Telegram user) raises 404 when user does not exist."""
    with pytest.raises(HTTPException) as exc_info:
        await get_telegram_user_by_id(user_id=99999, db=db_session)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"


# ----- Admin resolution (get_user_by_email, get_user_by_id) -----


@pytest.mark.asyncio
async def test_get_user_by_email_returns_admin(
        db_session: AsyncSession, admin_user: Admin
) -> None:
    """get_user_by_email returns the Admin when email exists."""
    result = await get_user_by_email(admin_user.email, db=db_session)
    assert result is not None
    assert result.id == admin_user.id
    assert result.email == admin_user.email


@pytest.mark.asyncio
async def test_get_user_by_email_returns_none_when_not_found(
        db_session: AsyncSession,
) -> None:
    """get_user_by_email returns None when no admin has the given email."""
    result = await get_user_by_email("nonexistent@example.com", db=db_session)
    assert result is None


@pytest.mark.asyncio
async def test_get_admin_by_id_returns_admin(
        db_session: AsyncSession, admin_user: Admin
) -> None:
    """get_user_by_id (Admin) returns the Admin when id exists."""
    result = await get_admin_by_id(admin_user.id, db=db_session)
    assert result is not None
    assert result.id == admin_user.id


@pytest.mark.asyncio
async def test_get_admin_by_id_returns_none_when_not_found(
        db_session: AsyncSession,
) -> None:
    """get_user_by_id (Admin) returns None when no admin has the given id."""
    result = await get_admin_by_id(99999, db=db_session)
    assert result is None


# ----- authenticate_user -----


@pytest.mark.asyncio
async def test_authenticate_user_returns_admin_when_credentials_valid(
        db_session: AsyncSession, admin_user: Admin
) -> None:
    """authenticate_user returns the Admin when email and password are correct."""
    result = await authenticate_user(
        admin_user.email, "testpass123", db=db_session
    )
    assert result is admin_user


@pytest.mark.asyncio
async def test_authenticate_user_raises_401_when_email_unknown(
        db_session: AsyncSession,
) -> None:
    """authenticate_user raises 401 when email does not exist."""
    with pytest.raises(HTTPException) as exc_info:
        await authenticate_user(
            "unknown@example.com", "anypass", db=db_session
        )
    assert exc_info.value.status_code == 401
    assert "Incorrect" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_authenticate_user_raises_401_when_password_wrong(
        db_session: AsyncSession, admin_user: Admin
) -> None:
    """authenticate_user raises 401 when password is incorrect."""
    with pytest.raises(HTTPException) as exc_info:
        await authenticate_user(
            admin_user.email, "wrongpassword", db=db_session
        )
    assert exc_info.value.status_code == 401
    assert "Incorrect" in str(exc_info.value.detail)


# ----- get_current_user (via minimal FastAPI app) -----


@pytest.mark.asyncio
async def test_get_current_user_returns_admin_with_valid_token(
        db_session: AsyncSession, admin_user: Admin
) -> None:
    """get_current_user resolves to Admin when Bearer token is valid."""
    from apps.api.auth.jwt import create_access_token

    async def override_get_db():
        yield db_session

    app = FastAPI()
    app.dependency_overrides[get_db_depends] = override_get_db

    @app.get("/me")
    async def me(current_user: Admin = Depends(get_current_user)):
        return {"id": current_user.id, "email": current_user.email}

    token = create_access_token(data={"sub": str(admin_user.id)})
    with TestClient(app) as client:
        response = client.get(
            "/me",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    assert response.json()["id"] == admin_user.id
    assert response.json()["email"] == admin_user.email


@pytest.mark.asyncio
async def test_get_current_user_raises_401_without_token(
        db_session: AsyncSession,
) -> None:
    """get_current_user leads to 401 when Authorization header is missing."""

    async def override_get_db():
        yield db_session

    app = FastAPI()
    app.dependency_overrides[get_db_depends] = override_get_db

    @app.get("/me")
    async def me(current_user: Admin = Depends(get_current_user)):
        return {"id": current_user.id}

    with TestClient(app) as client:
        response = client.get("/me")
    assert response.status_code == 401


# ----- Role guards (superadmin_required, admin_required, admin_or_superadmin_required) -----


def _make_admin(**kwargs) -> Admin:
    """Build a minimal Admin for role-guard tests."""
    defaults = {
        "id": 1,
        "email": "a@example.com",
        "hashed_password": "",
        "is_active": True,
        "is_super_admin": False,
        "registered_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return Admin(**defaults)


def test_superadmin_required_returns_user_when_superadmin() -> None:
    """superadmin_required returns the user when is_super_admin is True."""
    user = _make_admin(is_super_admin=True)
    result = superadmin_required(current_user=user)
    assert result is user


def test_superadmin_required_raises_403_when_not_superadmin() -> None:
    """superadmin_required raises 403 when is_super_admin is False."""
    user = _make_admin(is_super_admin=False)
    with pytest.raises(HTTPException) as exc_info:
        superadmin_required(current_user=user)
    assert exc_info.value.status_code == 403
    assert "SuperAdmin" in exc_info.value.detail


def test_admin_required_returns_user_when_active() -> None:
    """admin_required returns the user when is_active is True."""
    user = _make_admin(is_active=True)
    result = admin_required(current_user=user)
    assert result is user


def test_admin_required_raises_403_when_inactive() -> None:
    """admin_required raises 403 when is_active is False."""
    user = _make_admin(is_active=False)
    with pytest.raises(HTTPException) as exc_info:
        admin_required(current_user=user)
    assert exc_info.value.status_code == 403
    assert "Admin" in exc_info.value.detail


def test_admin_or_superadmin_required_returns_user_when_superadmin() -> None:
    """admin_or_superadmin_required returns the user when is_super_admin is True."""
    user = _make_admin(is_active=False, is_super_admin=True)
    result = admin_or_superadmin_required(current_user=user)
    assert result is user


def test_admin_or_superadmin_required_returns_user_when_active_admin() -> None:
    """admin_or_superadmin_required returns the user when is_active is True (and not superadmin)."""
    user = _make_admin(is_active=True, is_super_admin=False)
    result = admin_or_superadmin_required(current_user=user)
    assert result is user


def test_admin_or_superadmin_required_raises_403_when_inactive_not_superadmin() -> None:
    """admin_or_superadmin_required raises 403 when user is inactive and not superadmin."""
    user = _make_admin(is_active=False, is_super_admin=False)
    with pytest.raises(HTTPException) as exc_info:
        admin_or_superadmin_required(current_user=user)
    assert exc_info.value.status_code == 403
    assert "Admin or SuperAdmin" in exc_info.value.detail
