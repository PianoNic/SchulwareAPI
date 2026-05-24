"""DTOs for the stateless token refresh endpoint.

The caller (e.g. the Schuly Schulware plugin) owns persistence of context_state
and credentials. SchulwareAPI accepts state in, drives Playwright, returns the
updated state out — without storing anything itself.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


class RefreshTokenRequestDto(BaseModel):
    schulnetz_base_url: str = Field(..., description="The Schulnetz instance base URL, e.g. https://schulnetz.example.ch")
    context_state: Optional[dict[str, Any]] = Field(
        default=None,
        description="Browser context state (cookies + localStorage) from a previous successful refresh. None on first call.",
    )
    email: Optional[str] = Field(default=None, description="Required only when context_state is missing/expired and Microsoft SSO must be performed.")
    password: Optional[str] = Field(default=None, description="Required only when context_state is missing/expired and Microsoft SSO must be performed.")
    user_agent: Optional[str] = Field(default=None, description="UA string to replay with. Microsoft binds session cookies to UA; mismatch invalidates the session.")


class RefreshTokenResponseDto(BaseModel):
    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    session_id: Optional[str] = None
    web_session_user_id: Optional[str] = None
    web_session_trans_id: Optional[str] = None
    context_state: Optional[dict[str, Any]] = Field(
        default=None,
        description="Updated browser context state. The caller MUST persist this and pass it back on the next call.",
    )
    message: Optional[str] = None
