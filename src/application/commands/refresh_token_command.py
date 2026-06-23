"""Stateless Schulnetz login via headless `ms-entrance`.

Input in, output out: the caller passes credentials and/or a `session_cookies`
jar; we replay it through Microsoft Entra with `ms-entrance` — no browser — and
return fresh tokens, the web session, and the rotated `session_cookies` to
persist. SchulwareAPI stores nothing.

The flow is two cookie-sharing logins fed into Schulnetz's pure-HTTP exchanges:
  1. a "web" authorize round-trip → code → `capture_web_session` → PHPSESSID
  2. a "mobile" authorize round-trip → code → `exchange_code_for_tokens` → tokens
`ms_login` seeds the stored cookies for a silent SSO; if they're stale it falls
back to credentials (when provided), or raises `NeedsCredentials`.
"""

import asyncio
from dataclasses import dataclass

from entrance import LoginFailed, MfaRequired, NeedsCredentials
from entrance import login as ms_login
from mediatorx import ICommand, ICommandHandler

from src.api.auth.auth import exchange_code_for_tokens, generate_oauth_url
from src.application.dtos.refresh_dtos import LoginResponseDto
from src.application.services.web_session_service import capture_web_session, discover_web_oauth
from src.infrastructure.logging_config import get_logger

logger = get_logger("login_command")


@dataclass
class LoginCommand(ICommand[LoginResponseDto]):
    schulnetz_base_url: str
    session_cookies: list | None = None
    email: str | None = None
    password: str | None = None
    totp_secret: str | None = None
    totp_code: str | None = None
    user_agent: str | None = None


class LoginHandler(ICommandHandler[LoginCommand, LoginResponseDto]):
    """Mint fresh mobile + web tokens by replaying the cookie jar (or credentials)
    through Microsoft Entra headlessly via ms-entrance, then exchanging the
    resulting authorization codes at Schulnetz over plain HTTP."""

    async def handle(self, command: LoginCommand) -> LoginResponseDto:
        base = command.schulnetz_base_url.rstrip("/")
        cookies = command.session_cookies or None
        if cookies:
            logger.info("Login: replaying %d stored cookies", len(cookies))

        try:
            # 1) Web session round-trip → PHPSESSID + id/transid. Replicate the
            # browser: start OAuth from the school root (redirect_uri=`/`, no PKCE)
            # so the callback lands on `/` and renders the dashboard whose links
            # carry id/transid — authorize.php instead bounces the callback to
            # itself on a bare page. Drive the discovered Microsoft authorize URL,
            # then deliver the full callback (incl. session_state) back to `/` with
            # the anonymous session cookie the school set.
            web_authorize_url, anon_cookies = await discover_web_oauth(base)
            web_res = await self._login(web_authorize_url, command, cookies, ms_redirect=True)
            cookies = web_res.get("session_cookies") or cookies
            callback_url = web_res.get("redirect_url")
            if not callback_url:
                return LoginResponseDto(success=False, message="No web callback URL from login")
            web_cookies, web_info = await capture_web_session(
                base, callback_url, seed_cookies=anon_cookies
            )
            if not web_cookies or "PHPSESSID" not in web_cookies:
                return LoginResponseDto(success=False, message="No web session captured after login")
            session_id = web_cookies["PHPSESSID"]
            web_info = web_info or {}

            # 2) Mobile token round-trip → access/refresh tokens.
            mob = generate_oauth_url(base, auth_type="mobile")
            mob_res = await self._login(mob["auth_url"], command, cookies)
            cookies = mob_res.get("session_cookies") or cookies
            access_token, refresh_token = await exchange_code_for_tokens(
                mob_res["code"], mob["code_verifier"], base
            )

            logger.info("login: php=%s id=%s transid=%s token=%s",
                        bool(session_id), web_info.get("id"), web_info.get("transid"), bool(access_token))

            return LoginResponseDto(
                success=True,
                access_token=access_token,
                refresh_token=refresh_token,
                session_id=session_id,
                web_session_user_id=web_info.get("id"),
                web_session_trans_id=web_info.get("transid"),
                session_cookies=cookies,
                message="Tokens and session refreshed successfully",
            )

        except NeedsCredentials:
            return LoginResponseDto(
                success=False,
                message="Microsoft SSO session expired or no cookies given. Provide email + password to sign in.",
            )
        except MfaRequired as ex:
            return LoginResponseDto(
                success=False,
                message=f"MFA required: {ex}. Provide a TOTP secret/code or re-authenticate interactively.",
            )
        except LoginFailed as ex:
            return LoginResponseDto(success=False, message=f"Login failed: {ex}")
        except Exception as ex:
            logger.exception("Login failed")
            return LoginResponseDto(success=False, message=f"Login failed: {ex}")

    async def _login(self, authorize_url: str, command: LoginCommand, cookies, ms_redirect: bool = False):
        """Run the synchronous ms-entrance login off the event loop. Seeds the
        stored cookie jar for a silent SSO; falls back to credentials if given.
        `cookies` is always an inline list or None — never a file on disk.
        With ms_redirect=True the raw Microsoft → provider callback URL is returned
        (incl. session_state) without consuming the code."""
        return await asyncio.to_thread(
            ms_login,
            authorize_url,
            username=command.email,
            password=command.password,
            totp_secret=command.totp_secret,
            totp_code=command.totp_code,
            cookies=cookies,
            ms_redirect=ms_redirect,
        )
