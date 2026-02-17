import asyncio

from apps.news_parser.factory import get_parser
from apps.post_generator.generator import get_post_generator, PostGenerationService
from apps.tg_bot.publisher import PostPublisher
from database.repository import NewsRepository
from database.db import get_db
from apps.news_deduplicator.news_seen_cache import NewsSeenCache
from infrastructure.redis_client import get_redis_client
from logging_config import get_logger
from settings import settings
from apps.news_deduplicator.simhash_deduplicator import SimhashDeduplicator
from apps.news_deduplicator.text_normalizer import normalize_text

logger = get_logger(__name__)
repo = NewsRepository()
simhash_deduplicator = SimhashDeduplicator()


async def _process_one_source(source, cache: NewsSeenCache | None) -> None:
    """Parse one source, primary dedup via cache, save news_items with status=NEW (no SimHash yet)."""
    news_items = []
    try:
        parser = get_parser(source, limit=settings.NEWS_PARSE_LIMIT)
        news_items = await parser.parse()
    except Exception as e:
        logger.exception(f"Parse error for source {source.name} ({source.type}): {e}")
        return

    if cache is not None:
        to_create = await cache.filter_unseen(source.id, news_items)
    else:
        to_create = news_items

    if not to_create:
        if news_items:
            logger.info(
                f"Parsed {len(news_items)} items from source {source.url}, created 0 (all seen)"
            )
        return

    created = await repo.create_news_items_batch(to_create, source)

    if cache is not None and to_create:
        await cache.mark_seen_batch(source.id, to_create)

    if news_items:
        logger.info(
            f"Parsed {len(news_items)} items from source {source.url}, created {created}"
        )


async def parse_news_items():
    logger.info("Starting parsing cycle task")

    while True:
        sources = []

        try:
            sources = await repo.get_sources()
            logger.info(f"Parsing cycle: {len(sources)} enabled sources")
        except Exception as e:
            logger.exception(f"Parsing cycle error in `get_sources`: {e}")

        cache: NewsSeenCache | None = None
        try:
            redis = await get_redis_client()
            cache = NewsSeenCache(redis)
        except Exception as e:
            logger.warning(f"Redis cache unavailable, using DB only: {e}")

        await asyncio.gather(*[_process_one_source(source, cache) for source in sources])

        logger.debug("Parsing cycle finished, sleeping 60s")

        await asyncio.sleep(60)


async def deduplicate_news_items():
    """Process news_items with status=NEW: set simhash, is_duplicate, duplicate_of_id, status=DEDUPLICATED."""
    await asyncio.sleep(5)
    logger.info("SimHash deduplication task started")

    while True:
        items = await repo.get_new_items()
        if items:
            logger.info(f"Deduplicating {len(items)} new items")

        async with get_db() as db:
            for item in items:

                normalized = normalize_text(item.raw_text or "")
                if not normalized.strip():
                    await repo.update_news_item_dedup_result(
                        item.id,
                        simhash=0,
                        is_duplicate=True,
                        duplicate_of_id=None,
                    )
                    continue

                is_dup, dup_id, simhash = await simhash_deduplicator.check_duplicate(
                    db,
                    item.raw_text or "",
                    threshold=settings.SIMHASH_DEDUP_THRESHOLD,
                    title=item.title,
                    current_item_id=item.id,
                )
                await repo.update_news_item_dedup_result(
                    item.id,
                    simhash=simhash,
                    is_duplicate=is_dup,
                    duplicate_of_id=dup_id,
                )

        await asyncio.sleep(20)


async def create_posts():
    await asyncio.sleep(8)
    logger.info("Create posts task started")
    while True:
        items = await repo.get_deduplicated_items()
        if items:
            logger.info(f"Creating posts for {len(items)} deduplicated items")
        for item in items:
            await repo.create_post(item)

        await asyncio.sleep(20)


async def generate_posts():
    await asyncio.sleep(12)
    logger.info("Initializing post generator")
    generator = await get_post_generator()
    service = PostGenerationService(repo, generator)
    logger.info("Generate posts task started")

    while True:
        await service.process_pending_posts()

        await asyncio.sleep(20)


async def process_users_posts():
    logger.info("Process users posts task started")
    while True:
        users = await repo.get_users()
        posts = await repo.get_generated_posts()

        if users and posts:
            logger.info(f"Assigning {len(posts)} posts to {len(users)} users")
        for user in users:
            for post in posts:
                await repo.create_users_post(user, post)

        await repo.mark_posts_processed(posts)

        await asyncio.sleep(20)


async def publish_posts():
    logger.info("Publish posts task started")
    while True:
        users_posts = await repo.get_new_users_posts()
        if users_posts:
            logger.info(f"Publishing {len(users_posts)} user posts")

        for u_p in users_posts:
            publisher = PostPublisher(chat_id=u_p.user.chat_id)
            try:
                await publisher.publish(text=
                                        f"Source = {u_p.post.news.source.name}\n\n"
                                        f"generated text = {u_p.post.generated_text}")

                await repo.mark_users_post_published(u_p)
                logger.debug(f"Published post for user chat_id={u_p.user.chat_id}")
            except Exception as e:
                logger.exception(f"Publish failed for user chat_id={u_p.user.chat_id}: {e}")

        await asyncio.sleep(20)
