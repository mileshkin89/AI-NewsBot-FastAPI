import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.db import async_engine
from database.models import Admin
from apps.api.auth.dependencies import pwd_context

SUPERADMIN_EMAIL = "admin@example.com"
SUPERADMIN_PASSWORD = "change_me"


async def main():
    async_session = async_sessionmaker(async_engine, expire_on_commit=False)

    async with async_session() as session:
        exists = await session.execute(
            select(Admin).where(Admin.email == SUPERADMIN_EMAIL)
        )

        if exists.scalar_one_or_none():
            print("Superadmin already exists")
            return

        admin = Admin(
            email=SUPERADMIN_EMAIL,
            hashed_password=pwd_context.hash(SUPERADMIN_PASSWORD),
            is_super_admin=True,
            is_active=True,
        )

        session.add(admin)
        await session.commit()

        print("Superadmin created")


if __name__ == "__main__":
    asyncio.run(main())


# python src/scripts/create_superadmin.py