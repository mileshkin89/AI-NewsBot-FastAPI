"""
Deduplicate news items by SimHash and by vector similarity.

SimHash stage: processes items with status NEW.
Vector stage: processes items with status SIMHASH_DEDUPLICATED and is_duplicate=False.
"""
import asyncio

from apps.news_deduplicator.simhash_deduplicator import SimhashDeduplicator
from apps.news_deduplicator.vector_deduplicator import VectorDeduplicator
from apps.news_deduplicator.text_normalizer import normalize_text
from database.repository import NewsRepository
from database.db import get_db
from infrastructure.openai_embedding import get_open_ai_embedding_client
from logging_config import get_logger
from settings import settings

logger = get_logger(__name__)
repo = NewsRepository()
simhash_deduplicator = SimhashDeduplicator()
vector_deduplicator = VectorDeduplicator(get_open_ai_embedding_client)


async def deduplicate_news_items_simhash() -> None:
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


async def deduplicate_news_items_vector() -> None:
    """
    Process items with status SIMHASH_DEDUPLICATED and is_duplicate=False.

    Computes embedding, checks cosine similarity against existing vectors,
    and sets status to VECTOR_DEDUPLICATED.
    """
    await asyncio.sleep(8)
    logger.info("Vector deduplication task started")

    while True:
        items = await repo.get_simhash_deduplicated_items()
        if items:
            logger.info(f"Vector-deduplicating {len(items)} items")

        async with get_db() as db:
            for item in items:
                text = item.raw_text or ""
                if not text.strip():
                    await repo.update_news_item_vector_dedup_result(
                        item.id,
                        embedding=[],
                        is_duplicate=True,
                        duplicate_of_id=None,
                    )
                    continue

                try:
                    is_dup, dup_id, embedding = await vector_deduplicator.check_duplicate(
                        db,
                        text,
                        current_item_id=item.id,
                        threshold=settings.SEMANTIC_DEDUP_THRESHOLD,
                        lookback_hours=settings.SEMANTIC_DEDUP_LOOKBACK_HOURS,
                    )
                except Exception:
                    logger.exception(f"Vector dedup failed for item_id={item.id}")
                    continue

                await repo.update_news_item_vector_dedup_result(
                    item.id,
                    embedding=embedding,
                    is_duplicate=is_dup,
                    duplicate_of_id=dup_id,
                )

        await asyncio.sleep(20)