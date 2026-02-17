"""
Async repository for news pipeline data: sources, news items, posts, users, and user-post assignments.
Uses SQLAlchemy async sessions; each method manages its own session unless documented otherwise.
"""
from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from database.enams import NewsItemStatus, PostStatus, UsersPostStatus
from database.models import Source, User, NewsItem, Post, UsersPost
from apps.news_parser.schemas import NewsItem as NewsItemSchema
from apps.news_deduplicator.simhash import simhash_to_db
from logging_config import get_logger

logger = get_logger(__name__)


class NewsRepository:
    """
    Async repository for sources, news items, posts, users, and user-post links.
    All methods use their own database session (get_db) and commit/rollback internally.
    """

    # ---------- Sources ----------
    async def get_sources(self) -> list[Source]:
        """Return all enabled sources (Source.enabled is True)."""
        async with get_db() as db:
            result = await db.execute(
                select(Source).where(Source.enabled.is_(True))
            )
            sources = result.scalars().all()
        logger.debug(f"Fetched {len(sources)} enabled sources")
        return sources

    # ---------- Users ----------
    async def get_users(self) -> list[User]:
        """Return all active users (User.active is True)."""
        async with get_db() as db:
            result = await db.execute(
                select(User)
                .where(User.active.is_(True))
            )
            users = result.scalars().all()
        logger.debug(f"Fetched {len(users)} active users")
        return users

    # ---------- NewsItems ----------
    async def create_news_item(
            self,
            item: NewsItemSchema,
            source: Source,
            simhash: int | None = None,
            is_duplicate: bool = False,
            duplicate_of_id: int | None = None,
            status: NewsItemStatus | None = None,
    ) -> int:
        """
        Persist a single news item for the given source.

        On unique constraint violation (e.g. duplicate url), rolls back and returns 0.
        Returns 1 if the item was created successfully.
        """
        async with get_db() as db:
            return await self._add_news_item(
                db,
                item,
                source,
                simhash=simhash,
                is_duplicate=is_duplicate,
                duplicate_of_id=duplicate_of_id,
                status=status,
            )

    async def _add_news_item(
            self,
            db: AsyncSession,
            item: NewsItemSchema,
            source: Source,
            *,
            simhash: int | None = None,
            is_duplicate: bool = False,
            duplicate_of_id: int | None = None,
            status: NewsItemStatus | None = None,
    ) -> int:
        """
        Add one news item to the given session and commit.

        Used internally by create_news_item and by batch fallback. Returns 1 if committed,
        0 if IntegrityError (e.g. duplicate url) after rollback.
        """
        news_item = NewsItem(
            title=item.title or "",
            url=item.url,
            raw_text=item.raw_text or "",
            published_at=item.published_at,
            source_id=source.id,
            simhash=simhash_to_db(simhash) if simhash is not None else None,
            is_duplicate=is_duplicate,
            duplicate_of_id=duplicate_of_id,
            status=status if status is not None else NewsItemStatus.NEW,
        )
        db.add(news_item)
        try:
            await db.commit()
            logger.debug(f"Created news item: {(item.title or '')[:50]}... (source_id={source.id})")
            return 1
        except IntegrityError:
            await db.rollback()
            logger.debug(f"Duplicate news item skipped: {item.url}")
            return 0

    async def create_news_items_batch(self, items: list, source: Source) -> int:
        """
        Persist multiple news items for the given source (parser flow).

        Items are created with simhash=None, is_duplicate=False, duplicate_of_id=None,
        status=NEW. Each item must have title, url, raw_text, published_at.
        On bulk IntegrityError, falls back to inserting one by one.
        Returns the number of items successfully created.
        """
        if not items:
            return 0
        async with get_db() as db:
            for item in items:
                db.add(
                    NewsItem(
                        title=item.title or "",
                        url=item.url,
                        raw_text=item.raw_text or "",
                        published_at=item.published_at,
                        source_id=source.id,
                        simhash=None,
                        is_duplicate=False,
                        duplicate_of_id=None,
                        status=NewsItemStatus.NEW,
                    )
                )
            try:
                await db.commit()
                logger.debug(f"Created {len(items)} news items in batch (source_id={source.id})")
                return len(items)
            except IntegrityError:
                await db.rollback()
        created = 0
        for item in items:
            created += await self.create_news_item(item, source, simhash=None)
        return created

    async def update_news_item_dedup_result(
            self,
            news_item_id: int,
            simhash: int,
            is_duplicate: bool,
            duplicate_of_id: int | None,
    ) -> None:
        """
        Update a news item with SimHash deduplication result and set status to DEDUPLICATED.

        Called after the deduplication task processes an item (simhash computed,
        is_duplicate and duplicate_of_id set). The item will not be returned by
        get_deduplicated_items() if is_duplicate is True.
        """
        async with get_db() as db:
            await db.execute(
                update(NewsItem)
                .where(NewsItem.id == news_item_id)
                .values(
                    simhash=simhash_to_db(simhash),
                    is_duplicate=is_duplicate,
                    duplicate_of_id=duplicate_of_id,
                    status=NewsItemStatus.DEDUPLICATED,
                )
            )
            await db.commit()
        logger.debug(f"Updated dedup result for news_item_id={news_item_id}")

    async def get_new_items(self) -> list[NewsItem]:
        """Return news items with status NEW (pending SimHash deduplication)."""
        async with get_db() as db:
            result = await db.execute(
                select(NewsItem)
                .where(NewsItem.status == NewsItemStatus.NEW)
            )
            items = result.scalars().all()
        logger.debug(f"Fetched {len(items)} new news items")
        return items

    async def get_deduplicated_items(self) -> list[NewsItem]:
        """
        Return news items that passed deduplication and are unique (eligible for post creation).

        Filters by status=DEDUPLICATED and is_duplicate=False.
        """
        async with get_db() as db:
            result = await db.execute(
                select(NewsItem)
                .where(
                    NewsItem.status == NewsItemStatus.DEDUPLICATED,
                    NewsItem.is_duplicate.is_(False),
                )
            )
            items = result.scalars().all()
        logger.debug(f"Fetched {len(items)} deduplicated items")
        return items

    # ---------- Posts ----------
    async def create_post(self, item: NewsItem) -> None:
        """
        Create a Post linked to the given news item and set the item status to PROCESSED.

        On integrity error (e.g. post already exists for this news), still updates
        the news item status to PROCESSED.
        """
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
        """Return posts with status NEW (pending text generation)."""
        async with get_db() as db:
            result = await db.execute(
                select(Post)
                .where(Post.status == PostStatus.NEW)
            )
            posts = result.scalars().all()
        logger.debug(f"Fetched {len(posts)} new posts")
        return posts

    async def get_posts_pending_generation(self) -> list[tuple[int, str]]:
        """Return (post_id, raw_text) for all posts with status NEW (for generator input)."""
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
        """Return posts with status GENERATED, with news and source eagerly loaded."""
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
        """Save generated text for the post and set its status to GENERATED. No-op if post not found."""
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
        """Set status to PROCESSED for all given posts."""
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
        """Create a user-post assignment (NEW). Skips silently on duplicate (user_id, post_id)."""
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

    async def create_users_posts_for_post(self, users: list[User], post: Post) -> None:
        """
        Create user-post assignments for one post and all users (bulk insert).
        On IntegrityError falls back to inserting one by one via create_users_post.
        """
        if not users:
            return
        async with get_db() as db:
            for user in users:
                db.add(
                    UsersPost(
                        user_id=user.id,
                        post_id=post.id,
                        status=UsersPostStatus.NEW,
                    )
                )
            try:
                await db.commit()
                logger.debug(f"Created {len(users)} users_posts for post_id={post.id} (bulk)")
                return
            except IntegrityError:
                await db.rollback()
        for user in users:
            await self.create_users_post(user, post)

    async def get_new_users_posts(self) -> list[UsersPost]:
        """Return user-post assignments with status NEW, with user, post, news, and source loaded."""
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
        """Set the given user-post assignment status to PUBLISHED."""
        async with get_db() as db:
            await db.execute(
                update(UsersPost)
                .where(UsersPost.id == users_post.id)
                .values(status=UsersPostStatus.PUBLISHED)
            )
            await db.commit()
        logger.debug(f"Marked users_post as published: users_post_id={users_post.id}")
