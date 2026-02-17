"""Path parameter dependencies for entity resolution."""

from fastapi import Depends, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from sqlalchemy.orm import selectinload

from database.db import get_db_depends
from database.models import Category, NewsItem, Post, Source, User


async def get_category_by_id(
    category_id: int = Path(..., description="Category ID"),
    db: AsyncSession = Depends(get_db_depends),
) -> Category:
    """Resolve category by ID. Raises 404 if not found."""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return category


async def get_source_by_id(
    source_id: int = Path(..., description="Source ID"),
    db: AsyncSession = Depends(get_db_depends),
) -> Source:
    """Resolve source by ID. Raises 404 if not found."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    return source


async def get_post_by_id(
    post_id: int = Path(..., description="Post ID"),
    db: AsyncSession = Depends(get_db_depends),
) -> Post:
    """Resolve post by ID. Raises 404 if not found."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    return post


async def get_post_by_id_with_details(
    post_id: int = Path(..., description="Post ID"),
    db: AsyncSession = Depends(get_db_depends),
) -> Post:
    """Resolve post by ID with news_item, source and categories loaded. Raises 404 if not found."""
    result = await db.execute(
        select(Post)
        .where(Post.id == post_id)
        .options(
            selectinload(Post.news).selectinload(NewsItem.source).selectinload(Source.categories),
        )
    )
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    return post


async def get_user_by_id(
    user_id: int = Path(..., description="User ID"),
    db: AsyncSession = Depends(get_db_depends),
) -> User:
    """Resolve user by ID. Raises 404 if not found."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
