from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from database.db import get_db
from database.enams import NewsItemStatus, PostStatus, UsersPostStatus
from database.models import Source, User, NewsItem, Post, UsersPost
from logging_config import get_logger

logger = get_logger(__name__)


class NewsRepository:
    """Async repository for sources, news items, posts, and users."""

    # ---------- Sources ----------
    async def get_sources(self) -> list[Source]:
        """Return all enabled sources."""
        async with get_db() as db:
            result = await db.execute(
                select(Source).where(Source.enabled.is_(True))
            )
            sources = result.scalars().all()
        logger.debug(f"Fetched {len(sources)} enabled sources")
        return sources


    # ---------- Users ----------
    async def get_users(self) -> list[User]:
        """Return all active users."""
        async with get_db() as db:
            result = await db.execute(
                select(User)
                .where(User.active.is_(True))
            )
            users = result.scalars().all()
        logger.debug(f"Fetched {len(users)} active users")
        return users


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
                logger.debug(f"Created news item: {item.title[:50]}... (source_id={source.id})")
            except IntegrityError:
                await db.rollback()
                logger.debug(f"Duplicate news item skipped: {item.url}")


    async def get_new_items(self) -> list[NewsItem]:
        """Return news items with status NEW."""
        async with get_db() as db:
            result = await db.execute(
                select(NewsItem)
                .where(NewsItem.status == NewsItemStatus.NEW)
            )
            items = result.scalars().all()
        logger.debug(f"Fetched {len(items)} new news items")
        return items


    async def get_deduplicated_items(self) -> list[NewsItem]:
        """Return news items with status DEDUPLICATED."""
        async with get_db() as db:
            result = await db.execute(
                select(NewsItem)
                .where(NewsItem.status == NewsItemStatus.DEDUPLICATED)
            )
            items = result.scalars().all()
        logger.debug(f"Fetched {len(items)} deduplicated items")
        return items

    # ---------- Posts ----------
    async def create_post(self, item: NewsItem) -> None:
        """Create a post for the news item and set item status to PROCESSED."""
        async with get_db() as db:
            post = Post(news_id=item.id)
            db.add(post)

            item.status = NewsItemStatus.PROCESSED

            try:
                await db.commit()
                logger.debug(f"Created post for news_item_id={item.id}")
            except IntegrityError:
                await db.rollback()
                logger.warning(f"Failed to create post for news_item_id={item.id} (integrity error)")
                await db.execute(
                    update(NewsItem)
                    .where(NewsItem.id == item.id)
                    .values(status=NewsItemStatus.PROCESSED)
                )
                await db.commit()


    async def get_new_posts(self) -> list[Post]:
        """Return posts with status NEW."""
        async with get_db() as db:
            result = await db.execute(
                select(Post)
                .where(Post.status == PostStatus.NEW)
            )
            posts = result.scalars().all()
        logger.debug(f"Fetched {len(posts)} new posts")
        return posts


    async def get_posts_pending_generation(self) -> list[tuple[int, str]]:
        """Return (post_id, raw_text) for posts with status NEW."""
        async with get_db() as db:
            result = await db.execute(
                select(Post.id, NewsItem.raw_text)
                .select_from(Post)
                .join(NewsItem, Post.news_id == NewsItem.id)
                .where(Post.status == PostStatus.NEW)
            )
            pending = list(result.all())
        logger.debug(f"Fetched {len(pending)} posts pending generation")
        return pending


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
            posts = result.scalars().all()
        logger.debug(f"Fetched {len(posts)} generated posts")
        return posts


    async def mark_post_generated(self, post_id: int, text: str) -> None:
        """Save generated text for the post and set status to GENERATED."""
        async with get_db() as db:
            result = await db.execute(select(Post).where(Post.id == post_id))
            post = result.scalars().one_or_none()
            if post is None:
                logger.warning(f"Post not found for mark_post_generated: post_id={post_id}")
                return
            post.generated_text = text
            post.status = PostStatus.GENERATED
            await db.commit()
        logger.debug(f"Marked post as generated: post_id={post_id}")


    async def mark_posts_processed(self, posts: list[Post]) -> None:
        """Mark posts as processed."""

        post_ids = [p.id for p in posts]

        async with get_db() as db:
            await db.execute(
                update(Post)
                .where(Post.id.in_(post_ids))
                .values(status=PostStatus.PROCESSED)
            )
            await db.commit()
        logger.debug(f"Marked {len(posts)} posts as processed")


    # ---------- UsersPost ----------
    async def create_users_post(self, user: User, post: Post) -> None:
        async with get_db() as db:
            users_post = UsersPost(
                user_id=user.id,
                post_id=post.id,
                status=UsersPostStatus.NEW,
            )
            db.add(users_post)

            try:
                await db.commit()
                logger.debug(f"Created users_post: user_id={user.id}, post_id={post.id}")
            except IntegrityError:
                await db.rollback()
                logger.debug(f"Duplicate users_post skipped: user_id={user.id}, post_id={post.id}")

    async def get_new_users_posts(self) -> list[UsersPost]:
        async with get_db() as db:
            result = await db.execute(
                select(UsersPost)
                .where(UsersPost.status == UsersPostStatus.NEW)
                .options(
                    selectinload(UsersPost.user),
                    selectinload(UsersPost.post).selectinload(Post.news).selectinload(NewsItem.source),
                )
            )
            posts = result.scalars().all()
        logger.debug(f"Fetched {len(posts)} new users posts")
        return posts

    async def mark_users_post_published(self, users_post: UsersPost) -> None:
        async with get_db() as db:
            await db.execute(
                update(UsersPost)
                .where(UsersPost.id == users_post.id)
                .values(status=UsersPostStatus.PUBLISHED)
            )
            await db.commit()
        logger.debug(f"Marked users_post as published: users_post_id={users_post.id}")