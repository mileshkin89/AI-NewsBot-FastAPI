"""
Parse news from enabled sources and persist new items.

Runs in a loop: fetches sources, filters unseen items via cache,
creates news items with status NEW. SimHash is computed later by
the deduplicate_news task.
"""
import asyncio

from apps.news_parser.factory import get_parser
from apps.news_deduplicator.news_seen_cache import NewsSeenCache
from database.repository import NewsRepository
from infrastructure.redis_client import get_redis_client
from logging_config import get_logger
from settings import settings

logger = get_logger(__name__)
repo = NewsRepository()


async def _process_one_source(source, cache: NewsSeenCache | None) -> None:
    """
    Parse one source; primary dedup via cache; save news_items with status NEW.

    SimHash is not computed yet (done later by deduplicate_news_items).
    """
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


async def parse_news_items() -> None:
    """
    Run parsing cycle: fetch enabled sources, filter unseen, create news items.

    Uses Redis cache when available; otherwise creates items for all parsed
    results. Sleeps 60 seconds between cycles.
    """
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
