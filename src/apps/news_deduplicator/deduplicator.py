from sqlalchemy import select, and_

from database.db import get_db
from database.enams import NewsItemStatus
from database.models import NewsItem


class Deduplicator:

    async def deduplicate(self, news_item_id: int) -> None:
        async with get_db() as db:
            stmt = select(NewsItem).where(
                and_(
                    NewsItem.is_duplicate == False,
                    NewsItem.id == news_item_id,
                )
            )
            result = await db.execute(stmt)
            news_item = result.scalars().one_or_none()

            if news_item is None:
                return

            news_item.status = NewsItemStatus.DEDUPLICATED

            await db.commit()