import asyncio

from apps.tg_bot import start
from apps.tg_bot.menu import set_commands
from main_handler import (
    parse_news_items,
    deduplicate_news_items,
    create_posts,
    generate_posts,
    publish_posts,
    process_users_posts,
)
from logging_config import get_logger
from infrastructure.tg_bot import dp, bot

logger = get_logger(__name__)


def _log_task_exception(task: asyncio.Task) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.exception(f"Background task failed: {e}")


async def main():
    logger.info("Application starting")

    await set_commands()
    dp.include_router(start.router)
    logger.info("Setting bot commands and routers")

    tasks = [
        asyncio.create_task(parse_news_items()),
        asyncio.create_task(deduplicate_news_items()),
        asyncio.create_task(create_posts()),
        asyncio.create_task(generate_posts()),
        asyncio.create_task(process_users_posts()),
        asyncio.create_task(publish_posts()),
    ]
    for t in tasks:
        t.add_done_callback(_log_task_exception)
    logger.info(f"Created {len(tasks)} background tasks")

    try:
        logger.info("Starting bot polling")
        await dp.start_polling(bot)
    finally:
        logger.info("Stopping background tasks and closing bot session")
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
