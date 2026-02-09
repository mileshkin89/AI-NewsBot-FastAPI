import asyncio

from apps.news_parser.factory import get_parser
from apps.news_parser.schemas import NewsItem
from apps.post_generator.generator import get_post_generator, PostGenerator
from apps.tg_bot import start
from apps.tg_bot.menu import set_commands
from apps.tg_bot.publisher import PostPublisher

from database.repository import get_sources, get_users
from services.tg_bot import dp, bot


async def main():
    await set_commands()
    dp.include_router(start.router)

    sources = await get_sources()
    users = await get_users()

    await asyncio.sleep(20)

    publishers = [PostPublisher(chat_id=user.chat_id) for user in users]

    while True:
        for source in sources:
            parser = get_parser(source, limit=1)
            news_items = await parser.parse()

            print("source: ", source.name)

            for item in news_items:
                print("item.title: ", item.title)
                news_item = NewsItem(
                    title=item.title,
                    url=item.url,
                    raw_text=item.raw_text,
                    published_at=item.published_at,
                    source=source.name,
                )

                print("news text: ", news_item.raw_text)
                print("-" * 40)

                generator: PostGenerator = await get_post_generator()

                generated_text = await generator.generate_text(news_item.raw_text)
                print("generated_text: ", generated_text)
                print("=" * 40)

                for publisher in publishers:
                    await publisher.publish(
                        text = f"source: {source.name}\n"
                        f"news text: {news_item.raw_text}\n"
                        f"generated_text:  {generated_text}"
                    )

        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
