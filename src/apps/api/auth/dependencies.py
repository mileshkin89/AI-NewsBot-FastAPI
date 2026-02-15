"""Authentication dependencies for JWT validation and user resolution."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db_depends
from database.models import Admin
from settings import settings

from .jwt import verify_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

pwd_context = CryptContext(schemes=[settings.PASSWORD_HASH_SCHEME], deprecated="auto")


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db_depends)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = verify_access_token(token)
    except HTTPException:
        raise

    user_id: int = int(payload.get("sub"))
    if user_id is None:
        raise credentials_exception

    user_db = await get_user_by_id(user_id, db)
    if user_db is None:
        raise credentials_exception

    return user_db


async def get_user_by_email(
        email: str,
        db: AsyncSession = Depends(get_db_depends)
) -> Admin | None:
    stmt = select(Admin).where(Admin.email == email)
    result = await db.execute(stmt)
    return result.scalars().one_or_none()


async def get_user_by_id(
        user_id: int,
        db: AsyncSession = Depends(get_db_depends)
) -> Admin | None:
    stmt = select(Admin).where(Admin.id == user_id)
    result = await db.execute(stmt)
    return result.scalars().one_or_none()


async def authenticate_user(
        email: str,
        password: str,
        db: AsyncSession = Depends(get_db_depends)
):
    user_db = await get_user_by_email(email, db)
    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not pwd_context.verify(password, user_db.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_db


def superadmin_required(
    current_user: Admin = Depends(get_current_user),
) -> Admin:
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SuperAdmin privileges required",
        )
    return current_user


def admin_required(
    current_user: Admin = Depends(get_current_user),
) -> Admin:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def admin_or_superadmin_required(
    current_user: Admin = Depends(get_current_user),
) -> Admin:
    if current_user.is_super_admin:
        return current_user

    if current_user.is_active:
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin or SuperAdmin privileges required",
    )