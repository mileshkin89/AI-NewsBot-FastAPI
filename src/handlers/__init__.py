"""
Pipeline task handlers for the news bot.

Exposes background tasks: parse news, deduplicate, create/generate posts,
assign posts to users, and publish to Telegram. Import these and run
as asyncio tasks from the main entry point.
"""
from handlers.parse_news import parse_news_items
from handlers.deduplicate_news import deduplicate_news_items_simhash, deduplicate_news_items_vector
from handlers.create_posts import create_posts
from handlers.generate_posts import generate_posts
from handlers.process_users_posts import process_users_posts
from handlers.publish_posts import publish_posts

__all__ = [
    "parse_news_items",
    "deduplicate_news_items_simhash",
    "deduplicate_news_items_vector",
    "create_posts",
    "generate_posts",
    "process_users_posts",
    "publish_posts",
]
