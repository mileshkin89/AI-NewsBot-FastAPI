"""
Create superadmin user script.

Prompts for email and password interactively, then creates a superadmin
record in the database if one with the same email does not exist.

Usage:
    python -m scripts.create_superadmin
    python src/scripts/create_superadmin.py
    make create_superadmin
"""

import asyncio
import getpass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.db import async_engine
from database.models import Admin
from apps.api.auth.dependencies import pwd_context


def get_credentials() -> tuple[str, str]:
    """
    Prompt for superadmin email and password from the console.

    Asks for email, then password (hidden), then password confirmation.
    Exits with an error if any field is empty or passwords do not match.

    Returns:
        tuple[str, str]: (email, password) for the new superadmin.

    Raises:
        SystemExit: If email is empty, password is empty, or passwords differ.
    """
    email = input("Superadmin email: ").strip()
    if not email:
        raise SystemExit("Email cannot be empty")
    password = getpass.getpass("Superadmin password: ")
    if not password:
        raise SystemExit("Password cannot be empty")
    password_confirm = getpass.getpass("Confirm password: ")
    if password != password_confirm:
        raise SystemExit("Passwords do not match")
    return email, password


async def main() -> None:
    """
    Create a superadmin user in the database.

    Reads credentials via get_credentials(), checks that no admin with the same
    email exists, then creates and commits the new Admin with is_super_admin=True.
    """
    email, password = get_credentials()

    async_session = async_sessionmaker(async_engine, expire_on_commit=False)

    async with async_session() as session:
        # Skip creation if superadmin with this email already exists
        exists = await session.execute(
            select(Admin).where(Admin.email == email)
        )
        if exists.scalar_one_or_none():
            print("Superadmin already exists")
            return

        admin = Admin(
            email=email,
            hashed_password=pwd_context.hash(password),
            is_super_admin=True,
            is_active=True,
        )
        session.add(admin)
        await session.commit()

    print("Superadmin created")


if __name__ == "__main__":
    asyncio.run(main())