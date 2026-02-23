"""
Assign generated posts to users and mark posts as processed.

Runs in a loop: fetches all users and generated posts, creates
user-post links for each post for all users, then marks posts
as processed. Sleeps 20 seconds between cycles.
"""
import asyncio

from database.repository import NewsRepository
from logging_config import get_logger

logger = get_logger(__name__)
repo = NewsRepository()


async def _assign_post_to_users(users: list, post) -> None:
    """
    Assign one post to all users; use bulk insert with single-insert fallback.
    """
    await repo.create_users_posts_for_post(users, post)


async def process_users_posts() -> None:
    """
    Assign generated posts to users and mark posts as processed.

    For each generated post, creates user-post records for every user,
    then marks those posts as processed so they are not assigned again.
    """
    logger.info("Process users posts task started")
    while True:
        users = await repo.get_users()
        posts = await repo.get_generated_posts()

        if users and posts:
            logger.info(f"Assigning {len(posts)} posts to {len(users)} users")

        await asyncio.gather(*[_assign_post_to_users(users, post) for post in posts])

        await repo.mark_posts_processed(posts)

        await asyncio.sleep(20)
