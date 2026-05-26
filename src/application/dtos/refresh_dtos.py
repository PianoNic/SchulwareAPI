"""DTOs for the stateless token refresh endpoints.

The caller (e.g. the Schuly Schulware plugin) owns persistence of context_state
and credentials. SchulwareAPI accepts state in, drives Playwright, returns the
updated state out — without storing anything itself.
"""

from typing import Any
from pydantic import BaseModel, Field

class RefreshTokenRequestDto(BaseModel):
    """Stateless refresh using a previously captured browser context.

    This is the recommended refresh path. No credentials are sent — the request
    succeeds only if the supplied `context_state` is still valid. When it
    expires, re-authenticate via `/api/authenticate/oauth/mobile/url` rather
    than reaching for the deprecated credentials endpoint.
    """
    schulnetz_base_url: str = Field(..., description="The Schulnetz instance base URL, e.g. https://schulnetz.example.ch")
    context_state: dict[str, Any] = Field(
        ...,
        description="Browser context state (cookies + localStorage) from a previous successful refresh or OAuth capture.",
    )
    user_agent: str | None = Field(default=None, description="UA string to replay with. Microsoft binds session cookies to UA; mismatch invalidates the session.")

class RefreshTokenWithCredentialsRequestDto(BaseModel):
    """⚠️ DEPRECATED. Refresh by replaying full Microsoft SSO with credentials.

    Provided only as a last-resort fallback for the very first refresh after
    cold-start. Use `/api/authenticate/refresh` with a stored `context_state`
    for every subsequent call.
    """
    schulnetz_base_url: str = Field(..., description="The Schulnetz instance base URL, e.g. https://schulnetz.example.ch")
    email: str = Field(..., description="Microsoft SSO email.")
    password: str = Field(..., description="Microsoft SSO password.")
    user_agent: str | None = Field(default=None, description="UA string to use for the new session.")

class RefreshTokenResponseDto(BaseModel):
    success: bool
    access_token: str | None = None
    refresh_token: str | None = None
    session_id: str | None = None
    web_session_user_id: str | None = None
    web_session_trans_id: str | None = None
    context_state: dict[str, Any] | None = Field(
        default=None,
        description="Updated browser context state. The caller MUST persist this and pass it back on the next call.",
    )
    message: str | None = None
