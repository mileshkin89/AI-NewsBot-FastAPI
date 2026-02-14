"""Authentication schemas."""

from pydantic import BaseModel, Field


class Token(BaseModel):
    """OAuth2 token response."""

    access_token: str = Field(description="JWT access token for API authentication")
    token_type: str = Field(default="bearer", description="Token type")
