"""
Deduplicate news items by SimHash and update DB.

Processes news_items with status NEW: computes SimHash, determines
duplicates, sets is_duplicate, duplicate_of_id and status DEDUPLICATED.
"""
import asyncio

from apps.news_deduplicator.simhash_deduplicator import SimhashDeduplicator
from apps.news_deduplicator.text_normalizer import normalize_text
from database.repository import NewsRepository
from database.db import get_db
from logging_config import get_logger
from settings import settings

logger = get_logger(__name__)
repo = NewsRepository()
simhash_deduplicator = SimhashDeduplicator()


async def deduplicate_news_items() -> None:
    """
    Process news_items with status NEW.

    Sets simhash, is_duplicate, duplicate_of_id and status DEDUPLICATED.
    Sleeps 5 seconds before first run, then 20 seconds between cycles.
    """
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
