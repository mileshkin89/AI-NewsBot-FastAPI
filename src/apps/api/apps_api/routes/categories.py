"""Category management API endpoints."""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, or_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from apps.api.apps_api.dependencies import get_category_by_id
from apps.api.auth.dependencies import admin_or_superadmin_required
from apps.api.apps_api.utils import paginate
from apps.api.apps_api.schemas import (
    CategoriesCreate,
    CategoriesListResponse,
    CategoriesResponse,
    CategoriesUpdate,
    SourcesByCategoryResponse,
    UsersByCategoryResponse,
)
from database.db import get_db_depends
from database.enams import SourceType
from database.models import Category, Source, User, source_category, user_category

category_router = APIRouter(
    tags=["Categories"],
    dependencies=[Depends(admin_or_superadmin_required)],
)


@category_router.post(
    "/categories",
    response_model=CategoriesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create category",
    description="Create a new news category. Requires admin or superadmin role.",
)
async def create_category(
    category: CategoriesCreate,
    db: AsyncSession = Depends(get_db_depends),
) -> Category:
    """Create a new category."""
    new_category = Category(
        name=category.name,
        enabled=category.enabled,
    )
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    return new_category


@category_router.get(
    "/categories/{category_id}",
    response_model=CategoriesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get category",
    description="Retrieve a category by ID. Requires admin or superadmin role.",
)
async def get_category(
    category: Category | None = Depends(get_category_by_id),
) -> Category:
    """Return a single category by ID."""
    return category


@category_router.get(
    "/categories",
    response_model=CategoriesListResponse,
    status_code=status.HTTP_200_OK,
    summary="List categories",
    description="Retrieve a paginated list of categories with optional filters. Requires admin or superadmin role.",
)
async def get_categories(
    db: AsyncSession = Depends(get_db_depends),
    enabled: bool | None = Query(None, description="Filter by enabled status"),
    q: str | None = Query(None, description="Search by category name"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
) -> CategoriesListResponse:
    """List categories with pagination and optional search/filter."""
    stmt = select(Category)

    if enabled is not None:
        stmt = stmt.where(Category.enabled == enabled)

    if q and q.strip():
        search_term = f"%{q.strip()}%"
        stmt = stmt.where(Category.name.ilike(search_term))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    categories = result.scalars().all()

    return CategoriesListResponse(
        categories=categories,
        pagination=paginate(total, skip, limit, len(categories)),
    )


@category_router.get(
    "/categories/{category_id}/sources",
    response_model=SourcesByCategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="List sources by category",
    description="Retrieve sources assigned to a category with pagination. Requires admin or superadmin role.",
)
async def get_sources_by_category(
    category: Category | None = Depends(get_category_by_id),
    db: AsyncSession = Depends(get_db_depends),
    sources_enabled: bool | None = Query(None, description="Filter by source enabled status"),
    sources_type: SourceType | None = Query(None, description="Filter by source type"),
    q: str | None = Query(None, description="Search by source name or URL"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
) -> SourcesByCategoryResponse:
    """Return sources linked to the given category."""
    category_id = category.id
    base_stmt = (
        select(Source)
        .join(source_category)
        .where(source_category.c.category_id == category_id)
    )

    if sources_enabled is not None:
        base_stmt = base_stmt.where(Source.enabled == sources_enabled)
    if sources_type is not None:
        base_stmt = base_stmt.where(Source.type == sources_type)

    if q and q.strip():
        search = f"%{q.strip()}%"
        base_stmt = base_stmt.where(
            or_(
                Source.name.ilike(search),
                Source.url.ilike(search),
            )
        )

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = await db.scalar(count_stmt)

    data_stmt = base_stmt.offset(skip).limit(limit)
    result = await db.execute(data_stmt)
    sources = result.scalars().all()

    return SourcesByCategoryResponse(
        category=category,
        sources=sources,
        pagination=paginate(total, skip, limit, len(sources)),
    )


@category_router.get(
    "/categories/{category_id}/users",
    response_model=UsersByCategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="List users by category",
    description="Retrieve users subscribed to a category with pagination. Requires admin or superadmin role.",
)
async def get_users_by_category(
    category: Category | None = Depends(get_category_by_id),
    db: AsyncSession = Depends(get_db_depends),
    user_active: bool | None = Query(None, description="Filter by user active status"),
    q: str | None = Query(None, description="Search by Telegram chat_id"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
    sort_by: str = Query(
        "subscribed_at",
        description="Sort field",
        examples=["subscribed_at", "chat_id", "id"],
    ),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
) -> UsersByCategoryResponse:
    """Return users subscribed to the given category."""
    category_id = category.id
    base_stmt = (
        select(User)
        .join(user_category)
        .where(user_category.c.category_id == category_id)
    )

    if user_active is not None:
        base_stmt = base_stmt.where(User.active == user_active)

    if q and q.strip():
        search = f"%{q.strip()}%"
        base_stmt = base_stmt.where(cast(User.chat_id, String).ilike(search))

    sortable_fields = {
        "subscribed_at": User.subscribed_at,
        "chat_id": User.chat_id,
        "id": User.id,
    }
    field = sortable_fields.get(sort_by)
    if not field:
        raise HTTPException(status_code=400, detail=f"Cannot sort by '{sort_by}'")

    base_stmt = base_stmt.order_by(
        field.desc() if sort_order == "desc" else field.asc()
    )

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = await db.scalar(count_stmt)

    data_stmt = base_stmt.offset(skip).limit(limit)
    result = await db.execute(data_stmt)
    users = result.scalars().all()

    return UsersByCategoryResponse(
        category=category,
        users=users,
        pagination=paginate(total, skip, limit, len(users)),
    )


@category_router.patch(
    "/categories/{category_id}/deactivate",
    response_model=CategoriesResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate category",
    description="Set category enabled status to false. Requires admin or superadmin role.",
)
async def deactivate_category(
    category: Category | None = Depends(get_category_by_id),
    db: AsyncSession = Depends(get_db_depends),
) -> Category:
    """Deactivate a category."""
    if category.enabled:
        category.enabled = False
        await db.commit()
        await db.refresh(category)
    return category


@category_router.patch(
    "/categories/{category_id}/activate",
    response_model=CategoriesResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate category",
    description="Set category enabled status to true. Requires admin or superadmin role.",
)
async def activate_category(
    category: Category | None = Depends(get_category_by_id),
    db: AsyncSession = Depends(get_db_depends),
) -> Category:
    """Activate a category."""
    if not category.enabled:
        category.enabled = True
        await db.commit()
        await db.refresh(category)
    return category


@category_router.put(
    "/categories/{category_id}",
    response_model=CategoriesResponse,
    status_code=status.HTTP_200_OK,
    summary="Update category",
    description="Update category fields. Only provided fields are updated. Requires admin or superadmin role.",
)
async def update_category(
    up_category: CategoriesUpdate,
    category: Category | None = Depends(get_category_by_id),
    db: AsyncSession = Depends(get_db_depends),
) -> Category:
    """Update an existing category."""
    update_data = up_category.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(category, key, value)
        await db.commit()
        await db.refresh(category)
    return category


@category_router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete category",
    description="Permanently delete a category. Requires admin or superadmin role.",
)
async def delete_category(
    category: Category | None = Depends(get_category_by_id),
    db: AsyncSession = Depends(get_db_depends),
) -> None:
    """Delete a category."""
    await db.delete(category)
    await db.commit()
