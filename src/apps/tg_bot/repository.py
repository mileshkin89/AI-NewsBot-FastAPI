"""Data access for Telegram bot: categories and users."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.db import get_db
from database.models import Category, User


class CategoryRepository:
    """Reads and filters news categories."""

    def __init__(self, db: AsyncSession):
        """Args: db: Active async SQLAlchemy session."""
        self.db = db

    async def get_enabled_categories(self) -> list[Category]:
        """Return all categories with enabled=True."""
        result = await self.db.scalars(
            select(Category).where(Category.enabled.is_(True))
        )
        return result.all()

    async def get_categories_by_ids(self, category_ids: set[int]) -> list[Category]:
        """Return categories whose id is in category_ids. Returns [] if category_ids is empty."""
        if not category_ids:
            return []

        result = await self.db.scalars(
            select(Category).where(Category.id.in_(category_ids))
        )
        return result.all()


class UserRepository:
    """Reads and updates Telegram users and their category subscriptions."""

    def __init__(self, db: AsyncSession):
        """Args: db: Active async SQLAlchemy session."""
        self.db = db

    @staticmethod
    async def create_user(chat_id: int) -> None:
        """Create a user by chat_id if not exists; subscribe them to all enabled categories."""
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

            await db.refresh(user)

            result = await db.scalars(
                select(Category).where(Category.enabled == True)
            )
            _categories = result.all()
            user.categories.extend(_categories)

            await db.commit()

    async def get_by_chat_id(self, chat_id: int) -> User | None:
        """Return user with given chat_id and eager-loaded categories, or None."""
        return await self.db.scalar(
            select(User)
            .where(User.chat_id == chat_id)
            .options(selectinload(User.categories))
        )

    async def update_user_categories(self, user: User, categories: list[Category]) -> None:
        """Replace user's subscribed categories with the given list and commit."""
        user.categories.clear()
        user.categories.extend(categories)

        await self.db.commit()
