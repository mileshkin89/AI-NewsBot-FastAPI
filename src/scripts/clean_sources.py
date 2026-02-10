import asyncio
import logging

from sqlalchemy import delete

from database.db import get_db
from database.models import Source, NewsItem, Post

logger = logging.getLogger(__name__)


async def clean_sources() -> int:
    """
    Delete all sources from the database.

    Deletes in dependency order: Post -> NewsItem -> Source (FK constraints).
    Returns the number of sources deleted.

    Returns:
        Number of source records removed.
    """
    async with get_db() as db:
        await db.execute(delete(Post))
        await db.execute(delete(NewsItem))
        result = await db.execute(delete(Source))
        count = result.rowcount
        await db.commit()
        logger.info("Deleted %d source(s) from the database.", count)
        return count or 0


def main() -> None:
    """Entry point: run clean_sources and exit."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    deleted = asyncio.run(clean_sources())
    print(f"Clean completed. Removed {deleted} source(s).")


if __name__ == "__main__":
    main()
