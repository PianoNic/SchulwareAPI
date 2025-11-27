"""DTOs for basic authentication endpoints."""

from pydantic import BaseModel, Field
from typing import Optional


class AuthenticateRequestDto(BaseModel):
    """Request DTO for authentication endpoints."""
    email: str = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class AuthenticateMobileResponseDto(BaseModel):
    """Response DTO for mobile authentication."""
    success: bool = Field(..., description="Whether authentication was successful")
    access_token: Optional[str] = Field(None, description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")