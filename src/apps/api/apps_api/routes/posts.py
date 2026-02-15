"""Post management API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from apps.api.apps_api.dependencies import get_post_by_id
from apps.api.auth.dependencies import admin_or_superadmin_required
from apps.api.apps_api.utils import paginate
from apps.api.apps_api.schemas import PostCreate, PostListResponse, PostResponse, PostUpdate
from database.db import get_db_depends
from database.enams import PostStatus
from database.models import Post

post_router = APIRouter(
    tags=["Posts"],
    dependencies=[Depends(admin_or_superadmin_required)],
)


@post_router.post(
    "/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create post",
    description="Create a new post. Requires admin or superadmin role.",
)
async def create_post(
    post: PostCreate,
    db: AsyncSession = Depends(get_db_depends),
) -> Post:
    """Create a new post."""
    new_post = Post(generated_text=post.generated_text)
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post)
    return new_post


@post_router.get(
    "/posts",
    response_model=PostListResponse,
    status_code=status.HTTP_200_OK,
    summary="List posts",
    description="Retrieve a paginated list of posts with optional filters. Requires admin or superadmin role.",
)
async def get_posts(
    db: AsyncSession = Depends(get_db_depends),
    status: PostStatus | None = Query(None, description="Filter by post status"),
    q: str | None = Query(None, description="Search by post text"),
    date_from: datetime | None = Query(None, description="Start datetime (inclusive)"),
    date_to: datetime | None = Query(None, description="End datetime (inclusive)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
    sort_by: str = Query(
        "created_at",
        description="Sort field",
        examples=["created_at", "id"],
    ),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
) -> PostListResponse:
    """List posts with pagination and optional search/filter."""
    stmt = select(Post)

    if status is not None:
        stmt = stmt.where(Post.status == status)

    if q and q.strip():
        search_term = f"%{q.strip()}%"
        stmt = stmt.where(Post.generated_text.ilike(search_term))

    if date_from is not None:
        stmt = stmt.where(Post.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Post.created_at <= date_to)

    sortable_fields = {
        "created_at": Post.created_at,
        "id": Post.id,
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
    posts = result.scalars().all()

    return PostListResponse(
        posts=posts,
        pagination=paginate(total, skip, limit, len(posts)),
    )


@post_router.get(
    "/posts/{post_id}",
    response_model=PostResponse,
    status_code=status.HTTP_200_OK,
    summary="Get post",
    description="Retrieve a post by ID. Requires admin or superadmin role.",
)
async def get_post(
    post: Post | None = Depends(get_post_by_id),
) -> Post:
    """Return a single post by ID."""
    return post


@post_router.put(
    "/posts/{post_id}",
    response_model=PostResponse,
    status_code=status.HTTP_200_OK,
    summary="Update post",
    description="Update post fields. Only provided fields are updated. Requires admin or superadmin role.",
)
async def update_post(
    up_post: PostUpdate,
    post: Post | None = Depends(get_post_by_id),
    db: AsyncSession = Depends(get_db_depends),
) -> Post:
    """Update an existing post."""
    update_data = up_post.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(post, key, value)
        await db.commit()
        await db.refresh(post)
    return post


@post_router.delete(
    "/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete post",
    description="Permanently delete a post. Requires admin or superadmin role.",
)
async def delete_post(
    post: Post | None = Depends(get_post_by_id),
    db: AsyncSession = Depends(get_db_depends),
) -> None:
    """Delete a post."""
    await db.delete(post)
    await db.commit()
