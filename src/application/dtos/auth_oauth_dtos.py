"""DTOs for OAuth authentication endpoints."""

from pydantic import BaseModel, Field
from typing import Optional


# OAuth URL Generation Response DTOs

class MobileOAuthUrlResponseDto(BaseModel):
    """Response DTO for mobile OAuth URL generation."""
    authorization_url: str = Field(..., description="The OAuth authorization URL to redirect the user to")
    code_verifier: str = Field(..., description="PKCE code verifier that must be stored and used in the callback")


# Callback Request DTOs

class MobileCallbackRequestDto(BaseModel):
    """Request DTO for mobile OAuth callback."""
    code: str = Field(..., description="Authorization code from Microsoft")
    code_verifier: str = Field(..., description="PKCE code verifier that was generated during URL creation")
    state: Optional[str] = Field(None, description="State parameter for CSRF protection")


class WebCallbackRequestDto(BaseModel):
    """Request DTO for web OAuth callback."""
    code: str = Field(..., description="Authorization code from Microsoft")
    state: Optional[str] = Field(None, description="State parameter for CSRF protection")


# Callback Response DTOs

class MobileCallbackResponseDto(BaseModel):
    """Response DTO for mobile OAuth callback."""
    access_token: str = Field(..., description="JWT access token for API authentication")
    refresh_token: str = Field(..., description="Refresh token to obtain new access tokens")


class WebCallbackResponseDto(BaseModel):
    """Response DTO for web OAuth callback."""
    success: bool = Field(..., description="Whether the web authentication was successful")
    message: str = Field(..., description="Status message about the authentication")