"""DTOs for the unified, stateless Schulnetz login.

One endpoint, one shape: the caller (e.g. the Schuly Schulware plugin) passes in
credentials and/or a previously returned `session_cookies` jar, SchulwareAPI
replays it headlessly through Microsoft Entra (via `ms-entrance`), and returns
fresh tokens, the web session, and the rotated `session_cookies` to persist —
storing nothing itself. Input in, output out.
"""

from pydantic import BaseModel, Field


class LoginRequestDto(BaseModel):
    """Unified Schulnetz auth — one call for every sign-in path.

    Pass `session_cookies` from a previous response for a silent, passwordless
    re-auth, and/or `email` + `password` (+ TOTP) for a headless credential
    login. When both are present the cookies are tried first and the credentials
    are the fallback. No browser, no WebView.
    """

    schulnetz_base_url: str = Field(..., description="The Schulnetz instance base URL, e.g. https://schulnetz.example.ch")
    session_cookies: list[dict] | None = Field(
        default=None,
        description="Microsoft session cookies from a previous login, for a silent (passwordless) re-auth.",
    )
    email: str | None = Field(default=None, description="Microsoft SSO email (for a credential login or cold-start).")
    password: str | None = Field(default=None, description="Microsoft SSO password.")
    totp_secret: str | None = Field(default=None, description="Base32 TOTP secret, if the account has authenticator-app MFA. A fresh code is generated per attempt.")
    totp_code: str | None = Field(default=None, description="A precomputed 6-digit TOTP code, used as-is. Alternative to totp_secret.")
    user_agent: str | None = Field(default=None, description="UA to replay with. Microsoft binds session cookies to UA; a mismatch invalidates them.")


class LoginResponseDto(BaseModel):
    """Everything a caller needs from one login: mobile tokens, the web session,
    and the rotated cookie jar to persist for the next (passwordless) call."""

    success: bool
    access_token: str | None = None
    refresh_token: str | None = None
    session_id: str | None = None
    web_session_user_id: str | None = None
    web_session_trans_id: str | None = None
    session_cookies: list[dict] | None = Field(
        default=None,
        description="Rotated Microsoft session cookies. The caller MUST persist these and pass them back as session_cookies on the next call.",
    )
    message: str | None = None
