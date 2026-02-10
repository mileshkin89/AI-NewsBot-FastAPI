import asyncio

from apps.news_deduplicator.deduplicator import Deduplicator
from apps.news_parser.factory import get_parser
from apps.post_generator.generator import get_post_generator, PostGenerationService
from apps.tg_bot.publisher import PostPublisher
from database.repository import NewsRepository

repo = NewsRepository()


async def parse_news_items():
    while True:
        sources = await repo.get_sources()

        for source in sources:
            parser = get_parser(source, limit=1)
            news_items = await parser.parse()

            for item in news_items:
                await repo.create_news_item(item, source)

        await asyncio.sleep(60)


async def deduplicate_news_items():
    deduplicator = Deduplicator()

    while True:
        items = await repo.get_new_items()

        for item in items:
            await deduplicator.deduplicate(news_item_id=item.id)

        await asyncio.sleep(20)


async def create_posts():
    while True:
        items = await repo.get_deduplicated_items()

        for item in items:
            await repo.create_post(item)

        await asyncio.sleep(20)


async def generate_posts():
    generator = await get_post_generator()
    service = PostGenerationService(repo, generator)

    while True:
        await service.process_pending_posts()

        await asyncio.sleep(20)


async def publish_posts():
    while True:
        users = await repo.get_users()
        posts = await repo.get_generated_posts()

        for user in users:
            publisher = PostPublisher(chat_id=user.chat_id)

            for post in posts:
                await publisher.publish(
                    text=post.generated_text
                )

        await asyncio.sleep(20)

