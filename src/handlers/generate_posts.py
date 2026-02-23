"""
Generate post text for pending posts via OpenAI.

Runs in a loop: fetches posts with pending status, generates text
using the post generator service, and marks posts as GENERATED.
Sleeps 12 seconds before first run, then 20 seconds between cycles.
"""
import asyncio

from apps.post_generator.generator import get_post_generator, PostGenerationService
from database.repository import NewsRepository
from logging_config import get_logger

logger = get_logger(__name__)
repo = NewsRepository()


async def generate_posts() -> None:
    """
    Generate post text for pending posts via OpenAI and mark as GENERATED.

    Uses PostGenerationService to process all pending posts in each cycle.
    """
    await asyncio.sleep(12)
    logger.info("Initializing post generator")
    generator = await get_post_generator()
    service = PostGenerationService(repo, generator)
    logger.info("Generate posts task started")

    while True:
        await service.process_pending_posts()

        await asyncio.sleep(20)
