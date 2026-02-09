from sqlalchemy import select

from database.db import get_db
from database.models import Source


async def get_sources() -> list[Source]:
    async with get_db() as db:
        result = await db.execute(
            select(Source).where(Source.enabled.is_(True))
        )
        return result.scalars().all()
