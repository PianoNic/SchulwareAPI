"""DTOs for the unified, stateless Schulnetz login.

One endpoint, one shape: the caller passes in
credentials and/or a previously returned `session_cookies` jar, SchulwareAPI
replays it headlessly through Microsoft Entra (via `ms-entrance`), and returns
fresh tokens, the web session, and the rotated `session_cookies` to persist —
storing nothing itself. Input in, output out.
"""

from typing import Literal

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


class LoginMethodDto(BaseModel):
    """How a Schulnetz school signs users in."""

    method: Literal["microsoft", "native", "browser"] = Field(description="`microsoft`: Entra SSO (sign in with a Microsoft session or credentials). `native`: Schulnetz's own login form. `browser`: any other sign-in (e.g. a cantonal login); the user signs in in a browser started with /api/authenticate/browser/start.")


class BrowserLoginStartRequestDto(BaseModel):
    schulnetz_base_url: str = Field(..., description="The Schulnetz instance base URL")


class BrowserLoginStartDto(BaseModel):
    """Open `auth_url` in a browser; sign-in ends on a URL starting with `callback_url` that carries `code` and this `state`."""

    auth_url: str
    callback_url: str
    state: str
    code_verifier: str
    device_id: str


class BrowserLoginCompleteRequestDto(BaseModel):
    schulnetz_base_url: str
    code: str = Field(..., description="The `code` from the callback URL")
    code_verifier: str
    device_id: str


class MobileTokenRefreshRequestDto(BaseModel):
    schulnetz_base_url: str
    refresh_token: str
    device_id: str
