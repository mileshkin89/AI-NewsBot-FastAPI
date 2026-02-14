"""Telegram user management API endpoints."""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from apps.api.apps_api.dependencies import get_user_by_id
from apps.api.apps_api.utils import paginate
from apps.api.apps_api.schemas import (
    CategoriesByUserResponse,
    UserListResponse,
    UserResponse,
)
from database.db import get_db_depends
from database.models import Category, User, user_category

user_router = APIRouter(tags=["Users"])


@user_router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user",
    description="Retrieve a user by ID.",
)
async def get_user(
    user: User | None = Depends(get_user_by_id),
) -> User:
    """Return a single user by ID."""
    return user


@user_router.get(
    "/users/{user_id}/categories",
    response_model=CategoriesByUserResponse,
    status_code=status.HTTP_200_OK,
    summary="List categories by user",
    description="Retrieve categories subscribed by a user with pagination.",
)
async def get_categories_by_user(
    user: User | None = Depends(get_user_by_id),
    db: AsyncSession = Depends(get_db_depends),
    category_enabled: bool | None = Query(None, description="Filter by category enabled status"),
    q: str | None = Query(None, description="Search by category name"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
) -> CategoriesByUserResponse:
    """Return categories subscribed by the given user."""
    user_id = user.id
    base_stmt = (
        select(Category)
        .join(user_category)
        .where(user_category.c.user_id == user_id)
    )

    if category_enabled is not None:
        base_stmt = base_stmt.where(Category.enabled == category_enabled)

    if q and q.strip():
        search = f"%{q.strip()}%"
        base_stmt = base_stmt.where(Category.name.ilike(search))

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = await db.scalar(count_stmt)

    data_stmt = base_stmt.offset(skip).limit(limit)
    result = await db.execute(data_stmt)
    categories = result.scalars().all()

    return CategoriesByUserResponse(
        user=user,
        categories=categories,
        pagination=paginate(total, skip, limit, len(categories)),
    )


@user_router.get(
    "/users",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List users",
    description="Retrieve a paginated list of users with optional filters.",
)
async def get_users(
    db: AsyncSession = Depends(get_db_depends),
    active: bool | None = Query(None, description="Filter by user active status"),
    q: str | None = Query(None, description="Search by chat_id"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
    sort_by: str = Query(
        "subscribed_at",
        description="Sort field",
        examples=["subscribed_at", "id"],
    ),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
) -> UserListResponse:
    """List users with pagination and optional search/filter."""
    stmt = select(User)

    if active is not None:
        stmt = stmt.where(User.active == active)

    if q and q.strip():
        search_term = f"%{q.strip()}%"
        stmt = stmt.where(cast(User.chat_id, String).ilike(search_term))

    sortable_fields = {
        "subscribed_at": User.subscribed_at,
        "id": User.id,
    }
    field = sortable_fields.get(sort_by)
    if not field:
        raise HTTPException(status_code=400, detail=f"Cannot sort by '{sort_by}'")

    stmt = stmt.order_by(
        field.desc() if sort_order == "desc" else field.asc()
    )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()

    return UserListResponse(
        users=users,
        pagination=paginate(total, skip, limit, len(users)),
    )


@user_router.patch(
    "/users/{user_id}/deactivate",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate user",
    description="Set user active status to false.",
)
async def deactivate_user(
    user: User | None = Depends(get_user_by_id),
    db: AsyncSession = Depends(get_db_depends),
) -> User:
    """Deactivate a user."""
    if user.active:
        user.active = False
        await db.commit()
        await db.refresh(user)
    return user


@user_router.patch(
    "/users/{user_id}/activate",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate user",
    description="Set user active status to true.",
)
async def activate_user(
    user: User | None = Depends(get_user_by_id),
    db: AsyncSession = Depends(get_db_depends),
) -> User:
    """Activate a user."""
    if not user.active:
        user.active = True
        await db.commit()
        await db.refresh(user)
    return user


@user_router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Permanently delete a user.",
)
async def delete_user(
    user: User | None = Depends(get_user_by_id),
    db: AsyncSession = Depends(get_db_depends),
) -> None:
    """Delete a user."""
    await db.delete(user)
    await db.commit()
