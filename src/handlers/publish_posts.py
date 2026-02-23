"""
Publish user posts to Telegram with per-user delay.

Runs in a loop: fetches new user posts, groups them by user,
and publishes each user's posts sequentially with a configurable
delay between messages. Sleeps 20 seconds between cycles.
"""
import asyncio
from collections import defaultdict

from apps.tg_bot.publisher import PostPublisher
from database.repository import NewsRepository
from logging_config import get_logger
from settings import settings

logger = get_logger(__name__)
repo = NewsRepository()


def _build_publish_text(u_p) -> str:
    """
    Build publish text: category name(s) plus generated post text.

    Appends source category hashtags to the generated text when available.
    """
    base = u_p.post.generated_text or ""
    news = getattr(u_p.post, "news", None)
    source = getattr(news, "source", None) if news else None
    if source and getattr(source, "categories", None) and source.categories:
        names = ", ".join("#" + c.name for c in source.categories if c.name)
        if names:
            return f"{base}\n\n[{names}]"
    return base


async def _publish_one_user_post(u_p) -> None:
    """
    Publish one user post; log exceptions and do not re-raise.
    """
    publisher = PostPublisher(chat_id=u_p.user.chat_id)
    try:
        await publisher.publish(text=_build_publish_text(u_p))
        await repo.mark_users_post_published(u_p)
        logger.debug(f"Published post for user chat_id={u_p.user.chat_id}")
    except Exception as e:
        logger.exception(f"Publish failed for user chat_id={u_p.user.chat_id}: {e}")


async def _publish_user_posts_with_delay(user_posts: list) -> None:
    """
    Publish one user's posts sequentially with a delay between each.
    """
    for i, u_p in enumerate(user_posts):
        await _publish_one_user_post(u_p)
        if i < len(user_posts) - 1:
            await asyncio.sleep(settings.PUBLISH_DELAY_SEC)


async def publish_posts() -> None:
    """
    Publish new user posts to Telegram with per-user delay between messages.

    Groups pending user posts by user ID and publishes each user's queue
    in parallel; within each user, posts are sent with PUBLISH_DELAY_SEC
    between them.
    """
    logger.info("Publish posts task started")
    while True:
        users_posts = await repo.get_new_users_posts()
        if users_posts:
            logger.info(f"Publishing {len(users_posts)} user posts")

        by_user: dict[int, list] = defaultdict(list)
        for u_p in users_posts:
            by_user[u_p.user.id].append(u_p)

        await asyncio.gather(*[_publish_user_posts_with_delay(posts) for posts in by_user.values()])

        await asyncio.sleep(20)
