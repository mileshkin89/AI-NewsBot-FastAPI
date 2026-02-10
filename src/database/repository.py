from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from database.db import get_db
from database.enams import NewsItemStatus, PostStatus
from database.models import Source, User, NewsItem, Post


class NewsRepository:
    """Async repository for sources, news items, posts, and users."""

    # ---------- Sources ----------
    async def get_sources(self) -> list[Source]:
        """Return all enabled sources."""
        async with get_db() as db:
            result = await db.execute(
                select(Source).where(Source.enabled.is_(True))
            )
            return result.scalars().all()


    # ---------- Users ----------
    async def get_users(self) -> list[User]:
        """Return all active users."""
        async with get_db() as db:
            result = await db.execute(
                select(User)
                .where(User.active.is_(True))
            )
            return result.scalars().all()


    # ---------- NewsItems ----------
    async def create_news_item(self, item: NewsItem, source: Source) -> None:
        """Persist a news item for the given source; rollback on duplicate."""
        async with get_db() as db:
            news_item = NewsItem(
                title=item.title,
                url=item.url,
                raw_text=item.raw_text,
                published_at=item.published_at,
                source_id=source.id,
            )
            db.add(news_item)

            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()


    async def get_new_items(self) -> list[NewsItem]:
        """Return news items with status NEW."""
        async with get_db() as db:
            result = await db.execute(
                select(NewsItem)
                .where(NewsItem.status == NewsItemStatus.NEW)
            )
            return result.scalars().all()


    async def get_deduplicated_items(self) -> list[NewsItem]:
        """Return news items with status DEDUPLICATED."""
        async with get_db() as db:
            result = await db.execute(
                select(NewsItem)
                .where(NewsItem.status == NewsItemStatus.DEDUPLICATED)
            )
            return result.scalars().all()


    # ---------- Posts ----------
    async def create_post(self, item: NewsItem) -> None:
        """Create a post for the news item and set item status to PROCESSED."""
        async with get_db() as db:
            post = Post(news_id=item.id)
            db.add(post)

            item.status = NewsItemStatus.PROCESSED

            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()


    async def get_new_posts(self) -> list[Post]:
        """Return posts with status NEW."""
        async with get_db() as db:
            result = await db.execute(
                select(Post)
                .where(Post.status == PostStatus.NEW)
            )
            return result.scalars().all()


    async def get_posts_pending_generation(self) -> list[tuple[int, str]]:
        """Return (post_id, raw_text) for posts with status NEW."""
        async with get_db() as db:
            result = await db.execute(
                select(Post.id, NewsItem.raw_text)
                .select_from(Post)
                .join(NewsItem, Post.news_id == NewsItem.id)
                .where(Post.status == PostStatus.NEW)
            )
            return list(result.all())


    async def get_generated_posts(self) -> list[Post]:
        """Return posts with status GENERATED, with news and source loaded."""
        async with get_db() as db:
            result = await db.execute(
                select(Post)
                .where(Post.status == PostStatus.GENERATED)
                .options(
                    selectinload(Post.news)
                    .selectinload(NewsItem.source)
                )
            )
            return result.scalars().all()


    async def mark_post_generated(self, post_id: int, text: str) -> None:
        """Save generated text for the post and set status to GENERATED."""
        async with get_db() as db:
            result = await db.execute(select(Post).where(Post.id == post_id))
            post = result.scalars().one_or_none()
            if post is None:
                return
            post.generated_text = text
            post.status = PostStatus.GENERATED
            await db.commit()