import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.api.admin.routes import admin_router
from apps.api.apps_api.routes.categories import category_router
from apps.api.apps_api.routes.posts import post_router
from apps.api.apps_api.routes.sources import source_router
from apps.api.apps_api.routes.users import user_router
from apps.api.auth.routes import auth_router
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
from apps.post_generator.prompt_loader import load_prompts

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

    load_prompts()
    logger.info("Prompts from files loaded")

    tasks = [
        asyncio.create_task(parse_news_items()),
        # asyncio.create_task(deduplicate_news_items()),
        # asyncio.create_task(create_posts()),
        # asyncio.create_task(generate_posts()),
        # asyncio.create_task(process_users_posts()),
        # asyncio.create_task(publish_posts()),
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(main())
    yield


app = FastAPI(
    title="AI_news_bot",
    description="AI news telegram bot",
    lifespan=lifespan
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(category_router)
app.include_router(source_router)
app.include_router(user_router)
app.include_router(post_router)


@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "AI bot is running"}
