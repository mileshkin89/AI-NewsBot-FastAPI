"""
Create post records for deduplicated news items.

Runs in a loop: fetches items with status DEDUPLICATED, creates
one post per item and links it to the news. Sleeps 8 seconds before
first run, then 20 seconds between cycles.
"""
import asyncio

from database.repository import NewsRepository
from logging_config import get_logger

logger = get_logger(__name__)
repo = NewsRepository()


async def create_posts() -> None:
    """
    Create posts for deduplicated news items and link them to news.

    Processes items returned by repository in batches; one post per item.
    """
    await asyncio.sleep(8)
    logger.info("Create posts task started")
    while True:
        items = await repo.get_deduplicated_items()
        if items:
            logger.info(f"Creating posts for {len(items)} deduplicated items")
        for item in items:
            await repo.create_post(item)

        await asyncio.sleep(20)
