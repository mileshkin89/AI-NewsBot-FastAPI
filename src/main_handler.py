import asyncio

from apps.news_deduplicator.deduplicator import Deduplicator
from apps.news_parser.factory import get_parser
from apps.post_generator.generator import get_post_generator, PostGenerationService
from apps.tg_bot.publisher import PostPublisher
from database.repository import NewsRepository
from logging_config import get_logger

logger = get_logger(__name__)
repo = NewsRepository()


async def parse_news_items():
    logger.info("Starting parsing cycle task")

    while True:
        sources = []

        try:
            sources = await repo.get_sources()
            logger.info(f"Parsing cycle: {len(sources)} enabled sources")
        except Exception as e:
            logger.exception(f"Parsing cycle error in `get_sources`: {e}")

        for source in sources:
            try:
                parser = get_parser(source, limit=1)
                news_items = await parser.parse()
                for item in news_items:
                    await repo.create_news_item(item, source)
                if news_items:
                    logger.info(f"Parsed {len(news_items)} items from source: {source}")
            except Exception as e:
                logger.exception(f"Parse error for source {source.name} ({source.type}): {e}")

        logger.debug("Parsing cycle finished, sleeping 60s")


        await asyncio.sleep(60)


async def deduplicate_news_items():
    deduplicator = Deduplicator()
    logger.info("Deduplication task started")

    while True:
        items = await repo.get_new_items()
        if items:
            logger.info(f"Deduplicating {len(items)} new items")
        for item in items:
            await deduplicator.deduplicate(news_item_id=item.id)
        await asyncio.sleep(20)


async def create_posts():
    logger.info("Create posts task started")
    while True:
        items = await repo.get_deduplicated_items()
        if items:
            logger.info(f"Creating posts for {len(items)} deduplicated items")
        for item in items:
            await repo.create_post(item)
        await asyncio.sleep(20)


async def generate_posts():
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
                await publisher.publish(text=u_p.post.generated_text)
                await repo.mark_users_post_published(u_p)
                logger.debug(f"Published post for user chat_id={u_p.user.chat_id}")
            except Exception as e:
                logger.exception(f"Publish failed for user chat_id={u_p.user.chat_id}: {e}")

        await asyncio.sleep(20)
