"""Admin API schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class AdminCreate(BaseModel):
    """Schema for creating an admin user."""

    email: EmailStr = Field(max_length=100, description="Admin email address")
    name: str | None = Field(default=None, max_length=50, description="Admin display name")
    password: str = Field(min_length=5, max_length=100, description="Admin password")


class AdminResponse(BaseModel):
    """Admin user representation in API responses."""

    id: int
    email: EmailStr
    is_active: bool
    name: str | None = None
    last_login: datetime | None = None

    model_config = {"from_attributes": True}


class AdminListResponse(BaseModel):
    """List of admin users."""

    admins: list[AdminResponse]

    model_config = {"from_attributes": True}
