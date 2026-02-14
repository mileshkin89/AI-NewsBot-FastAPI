"""Admin user management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from apps.api.auth.dependencies import (
    get_user_by_email,
    get_user_by_id,
    pwd_context,
    superadmin_required,
)
from database.db import get_db_depends
from database.models import Admin

from .schemas import AdminCreate, AdminListResponse, AdminResponse

admin_router = APIRouter(tags=["Admins"])


@admin_router.get(
    "/admins",
    dependencies=[Depends(superadmin_required)],
    response_model=AdminListResponse,
    status_code=status.HTTP_200_OK,
    summary="List admins",
    description="Retrieve all admin users. Requires superadmin role.",
)
async def get_admins(
    db: AsyncSession = Depends(get_db_depends),
) -> AdminListResponse:
    """Return list of all admin users."""
    stmt = select(Admin).order_by(Admin.id)
    result = await db.execute(stmt)
    admins = result.scalars().all()
    return AdminListResponse(admins=admins)


@admin_router.post(
    "/admins",
    dependencies=[Depends(superadmin_required)],
    response_model=AdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create admin",
    description="Create a new admin user. Requires superadmin role.",
)
async def create_admin(
    admin: AdminCreate,
    db: AsyncSession = Depends(get_db_depends),
) -> Admin:
    """Create a new admin user."""
    existing = await get_user_by_email(admin.email, db)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin already exists",
        )

    admin_db = Admin(
        email=admin.email,
        name=admin.name,
        hashed_password=pwd_context.hash(admin.password),
        is_active=True,
        is_super_admin=False,
    )

    db.add(admin_db)
    await db.commit()
    await db.refresh(admin_db)

    return admin_db


@admin_router.patch(
    "/admins/{admin_id}/deactivate",
    dependencies=[Depends(superadmin_required)],
    status_code=status.HTTP_200_OK,
    summary="Deactivate admin",
    description="Deactivate an admin user. Requires superadmin role.",
)
async def deactivate_admin(
    admin_id: int,
    db: AsyncSession = Depends(get_db_depends),
) -> None:
    """Deactivate an admin user."""
    admin = await get_user_by_id(admin_id, db)
    admin.is_active = False
    await db.commit()
