"""Authentication API endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from apps.api.auth.dependencies import (
    authenticate_user,
    get_current_user,
    get_user_by_id,
)
from apps.api.auth.jwt import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from apps.api.auth.schemas import Token
from apps.api.auth.utils import set_refresh_token_cookie
from database.db import get_db_depends
from database.models import Admin

auth_router = APIRouter(tags=["Auth"], prefix="/auth")


@auth_router.post(
    "/token",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Login",
    description="Authenticate with email and password. Returns JWT access token and sets refresh token in cookie.",
)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_depends),
) -> dict:
    """Authenticate user and return access token."""
    user_db = await authenticate_user(form_data.username, form_data.password, db)

    access_token = create_access_token(data={"sub": str(user_db.id)})
    refresh_token = create_refresh_token(data={"sub": str(user_db.id)})

    user_db.refresh_token = refresh_token
    user_db.last_login = datetime.now(timezone.utc)
    await db.commit()

    set_refresh_token_cookie(response, refresh_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@auth_router.post(
    "/token/refresh",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Refresh token",
    description="Obtain new access token using refresh token from cookie.",
)
async def refresh_token(
    response: Response,
    refresh_token: str = Cookie(None, alias="refresh_token"),
    db: AsyncSession = Depends(get_db_depends),
) -> dict:
    """Refresh access token using stored refresh token."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found in cookies",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_refresh_token(refresh_token)
    user_id: int = int(payload.get("sub"))

    user_db = await get_user_by_id(user_id, db)

    if user_db is None or user_db.refresh_token != refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    access_token = create_access_token(data={"sub": str(user_db.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user_db.id)})

    user_db.refresh_token = new_refresh_token
    await db.commit()

    set_refresh_token_cookie(response, new_refresh_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@auth_router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout",
    description="Invalidate current session and clear refresh token cookie.",
)
async def logout(
    response: Response,
    current_user: Admin = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_depends),
) -> dict:
    """Log out current user and clear session."""
    current_user.refresh_token = None
    await db.commit()

    response.delete_cookie(key="refresh_token")

    return {"message": "Successfully logged out"}
