"""Pydantic schemas for API request/response models."""

from datetime import datetime

from pydantic import BaseModel, Field

from database.enams import PostStatus, SourceType


# --------------
# Categories
# --------------
class CategoriesCreate(BaseModel):
    """Schema for creating a new category."""

    name: str = Field(max_length=100, description="Category display name")
    enabled: bool = Field(default=True, description="Whether the category is active")


class CategoriesUpdate(BaseModel):
    """Schema for updating an existing category."""

    name: str | None = Field(default=None, max_length=100, description="Category display name")
    enabled: bool | None = Field(default=None, description="Whether the category is active")


class CategoriesResponse(BaseModel):
    """Category representation in API responses."""

    id: int
    name: str
    enabled: bool

    model_config = {"from_attributes": True}


class CategoriesListResponse(BaseModel):
    """Paginated list of categories."""

    categories: list[CategoriesResponse]
    pagination: dict | None = None


class SourcesByCategoryResponse(BaseModel):
    """Sources assigned to a category with pagination."""

    category: CategoriesResponse
    pagination: dict | None = None
    sources: list["SourceResponse"]

    model_config = {"from_attributes": True}


class UsersByCategoryResponse(BaseModel):
    """Users subscribed to a category with pagination."""

    category: CategoriesResponse
    pagination: dict | None = None
    users: list["UserResponse"]

    model_config = {"from_attributes": True}


# --------------
# Sources
# --------------
class SourceCreate(BaseModel):
    """Schema for creating a news source."""

    name: str = Field(max_length=250, description="Source display name")
    type: SourceType = Field(description="Source type: site or telegram")
    url: str = Field(max_length=500, description="Source URL or identifier")
    title_selector: str | None = Field(default=None, max_length=500, description="CSS selector for article titles")
    enabled: bool = Field(default=True, description="Whether the source is active")


class SourceUpdate(BaseModel):
    """Schema for updating an existing source."""

    name: str | None = Field(default=None, max_length=250, description="Source display name")
    type: SourceType | None = Field(default=None, description="Source type")
    url: str | None = Field(default=None, max_length=500, description="Source URL")
    title_selector: str | None = Field(default=None, max_length=500, description="Title selector")
    enabled: bool | None = Field(default=None, description="Whether the source is active")


class SourceResponse(BaseModel):
    """Source representation in API responses."""

    id: int
    name: str
    type: SourceType
    url: str
    title_selector: str | None
    enabled: bool

    model_config = {"from_attributes": True}


class SourceListResponse(BaseModel):
    """Paginated list of sources."""

    sources: list[SourceResponse]
    pagination: dict | None = None


class CategoriesBySourceResponse(BaseModel):
    """Categories assigned to a source with pagination."""

    source: SourceResponse
    pagination: dict | None = None
    categories: list["CategoriesResponse"]

    model_config = {"from_attributes": True}


# --------------
# Users
# --------------
class UserResponse(BaseModel):
    """Telegram user representation in API responses."""

    id: int
    chat_id: int
    active: bool
    subscribed_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Paginated list of users."""

    users: list[UserResponse]
    pagination: dict | None = None


class CategoriesByUserResponse(BaseModel):
    """Categories subscribed by a user with pagination."""

    user: UserResponse
    pagination: dict | None = None
    categories: list["CategoriesResponse"]

    model_config = {"from_attributes": True}


# --------------
# Posts
# --------------
class PostCreate(BaseModel):
    """Schema for creating a post."""

    generated_text: str | None = Field(default=None, max_length=2000, description="AI-generated post text")


class PostUpdate(BaseModel):
    """Schema for updating an existing post."""

    generated_text: str | None = Field(default=None, max_length=2000, description="Post text")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    status: PostStatus | None = Field(default=None, description="Post processing status")


class PostResponse(BaseModel):
    """Post representation in API responses."""

    id: int
    generated_text: str | None = Field(default=None, max_length=2000)
    created_at: datetime
    status: PostStatus

    model_config = {"from_attributes": True}


class PostListResponse(BaseModel):
    """Paginated list of posts."""

    posts: list[PostResponse]
    pagination: dict | None = None