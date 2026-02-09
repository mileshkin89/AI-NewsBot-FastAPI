from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database.db import get_db
from database.models import User


async def create_user(chat_id: int) -> None:
    async with get_db() as db:
        existing_user = await db.scalar(
            select(User).where(User.chat_id == chat_id)
        )
        if existing_user:
            return

        user = User(
            chat_id=chat_id,
        )
        db.add(user)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
