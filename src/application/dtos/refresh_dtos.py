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

class RefreshTokenGrantRequestDto(BaseModel):
    """⚗️ EXPERIMENTAL (#121). Direct OAuth2 refresh_token grant — no browser.

    Submits `grant_type=refresh_token` to `{schulnetz_base_url}/token.php` with
    the supplied `refresh_token`. If Schulnetz honours the grant, this becomes
    the cheapest refresh path (milliseconds, no Chromium) and `/refresh`
    (context_state replay) only stays around as a fallback.

    The refresh_token must come from an authorization flow that included the
    `offline_access` scope. With the spike merged, every new OAuth round-trip
    automatically requests it.
    """
    schulnetz_base_url: str = Field(..., description="The Schulnetz instance base URL.")
    refresh_token: str = Field(..., description="The refresh_token previously issued by /token.php.")

class RefreshTokenGrantResponseDto(BaseModel):
    """Raw response from /token.php for the refresh_token grant.

    Fields are passed through verbatim so the spike can observe exactly what
    Schulnetz returns — including any non-standard fields or error shapes.
    """
    success: bool
    status_code: int = Field(..., description="HTTP status code from /token.php — non-200 means the grant was rejected.")
    access_token: str | None = None
    refresh_token: str | None = Field(default=None, description="A new refresh_token if Schulnetz rotates them; otherwise null.")
    expires_in: int | None = None
    token_type: str | None = None
    scope: str | None = None
    raw_response: dict[str, Any] | None = Field(default=None, description="Full /token.php JSON body, for spike inspection.")
    message: str | None = None

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
