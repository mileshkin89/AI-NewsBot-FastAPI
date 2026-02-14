"""News source management API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from apps.api.apps_api.dependencies import get_source_by_id
from apps.api.apps_api.utils import paginate
from apps.api.apps_api.schemas import (
    CategoriesBySourceResponse,
    SourceCreate,
    SourceListResponse,
    SourceResponse,
    SourceUpdate,
)
from database.db import get_db_depends
from database.enams import SourceType
from database.models import Category, Source, source_category

source_router = APIRouter(tags=["Sources"])


@source_router.post(
    "/sources",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create source",
    description="Create a new news source.",
)
async def create_source(
    source: SourceCreate,
    db: AsyncSession = Depends(get_db_depends),
) -> Source:
    """Create a new news source."""
    new_source = Source(
        name=source.name,
        type=source.type,
        url=source.url,
        title_selector=source.title_selector,
        enabled=source.enabled,
    )
    db.add(new_source)
    await db.commit()
    await db.refresh(new_source)
    return new_source


@source_router.get(
    "/sources",
    response_model=SourceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List sources",
    description="Retrieve a paginated list of sources with optional filters.",
)
async def get_sources(
    db: AsyncSession = Depends(get_db_depends),
    enabled: bool | None = Query(None, description="Filter by enabled status"),
    type: SourceType | None = Query(None, description="Filter by source type"),
    q: str | None = Query(None, description="Search by source name"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
) -> SourceListResponse:
    """List sources with pagination and optional search/filter."""
    stmt = select(Source)

    if enabled is not None:
        stmt = stmt.where(Source.enabled == enabled)
    if type is not None:
        stmt = stmt.where(Source.type == type)

    if q and q.strip():
        search_term = f"%{q.strip()}%"
        stmt = stmt.where(Source.name.ilike(search_term))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    sources = result.scalars().all()

    return SourceListResponse(
        sources=sources,
        pagination=paginate(total, skip, limit, len(sources)),
    )


@source_router.get(
    "/source/{source_id}/categories",
    response_model=CategoriesBySourceResponse,
    status_code=status.HTTP_200_OK,
    summary="List categories by source",
    description="Retrieve categories assigned to a source with pagination.",
)
async def get_categories_by_source(
    source: Source | None = Depends(get_source_by_id),
    db: AsyncSession = Depends(get_db_depends),
    category_enabled: bool | None = Query(None, description="Filter by category enabled status"),
    q: str | None = Query(None, description="Search by category name"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
) -> CategoriesBySourceResponse:
    """Return categories linked to the given source."""
    source_id = source.id
    base_stmt = (
        select(Category)
        .join(source_category)
        .where(source_category.c.source_id == source_id)
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

    return CategoriesBySourceResponse(
        source=source,
        categories=categories,
        pagination=paginate(total, skip, limit, len(categories)),
    )


@source_router.get(
    "/sources/{source_id}",
    response_model=SourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get source",
    description="Retrieve a source by ID.",
)
async def get_source(
    source: Source | None = Depends(get_source_by_id),
) -> Source:
    """Return a single source by ID."""
    return source


@source_router.patch(
    "/sources/{source_id}/deactivate",
    response_model=SourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate source",
    description="Set source enabled status to false.",
)
async def deactivate_source(
    source: Source | None = Depends(get_source_by_id),
    db: AsyncSession = Depends(get_db_depends),
) -> Source:
    """Deactivate a source."""
    if source.enabled:
        source.enabled = False
        await db.commit()
        await db.refresh(source)
    return source


@source_router.patch(
    "/sources/{source_id}/activate",
    response_model=SourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate source",
    description="Set source enabled status to true.",
)
async def activate_source(
    source: Source | None = Depends(get_source_by_id),
    db: AsyncSession = Depends(get_db_depends),
) -> Source:
    """Activate a source."""
    if not source.enabled:
        source.enabled = True
        await db.commit()
        await db.refresh(source)
    return source


@source_router.put(
    "/sources/{source_id}",
    response_model=SourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update source",
    description="Update source fields. Only provided fields are updated.",
)
async def update_source(
    up_source: SourceUpdate,
    source: Source | None = Depends(get_source_by_id),
    db: AsyncSession = Depends(get_db_depends),
) -> Source:
    """Update an existing source."""
    update_data = up_source.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(source, key, value)
        await db.commit()
        await db.refresh(source)
    return source


@source_router.delete(
    "/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete source",
    description="Permanently delete a source.",
)
async def delete_source(
    source: Source | None = Depends(get_source_by_id),
    db: AsyncSession = Depends(get_db_depends),
) -> None:
    """Delete a source."""
    await db.delete(source)
    await db.commit()
