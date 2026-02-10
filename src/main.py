import asyncio

from apps.tg_bot import start
from apps.tg_bot.menu import set_commands
from main_handler import parse_news_items, deduplicate_news_items, create_posts, generate_posts, publish_posts

from services.tg_bot import dp, bot


async def main():
    await set_commands()
    dp.include_router(start.router)

    tasks = [
        asyncio.create_task(parse_news_items()),
        asyncio.create_task(deduplicate_news_items()),
        asyncio.create_task(create_posts()),
        asyncio.create_task(generate_posts()),
        asyncio.create_task(publish_posts()),
    ]

    try:
        await dp.start_polling(bot)
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
