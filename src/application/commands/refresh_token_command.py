"""Stateless token + session refresh via headless `ms-entrance` login.

State contract: the caller passes `context_state` (a cookie jar) in; we replay
it through Microsoft Entra with the `ms-entrance` package — no browser — and on
success return the updated jar for the caller to persist. SchulwareAPI itself
stores nothing.

The flow is two cookie-sharing logins fed into Schulnetz's existing pure-HTTP
exchanges:
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
from src.application.dtos.refresh_dtos import RefreshTokenResponseDto
from src.application.services.web_session_service import capture_web_session
from src.infrastructure.logging_config import get_logger

logger = get_logger("refresh_token_command")


@dataclass
class RefreshTokenCommand(ICommand[RefreshTokenResponseDto]):
    schulnetz_base_url: str
    context_state: dict | None = None
    email: str | None = None
    password: str | None = None
    totp_secret: str | None = None
    user_agent: str | None = None


class RefreshTokenHandler(ICommandHandler[RefreshTokenCommand, RefreshTokenResponseDto]):
    """Mint fresh mobile + web tokens by replaying the stored cookie jar through
    Microsoft Entra (headless, via ms-entrance), then exchanging the resulting
    authorization codes at Schulnetz over plain HTTP."""

    async def handle(self, command: RefreshTokenCommand) -> RefreshTokenResponseDto:
        base = command.schulnetz_base_url.rstrip("/")
        cookies = _cookies_from_state(command.context_state)
        if cookies:
            logger.info("Refresh: replaying %d stored cookies", len(cookies))

        try:
            # 1) Web session round-trip → PHPSESSID + id/transid.
            web = generate_oauth_url(base, auth_type="web")
            web_res = await self._login(web["auth_url"], command, cookies)
            cookies = web_res.get("session_cookies") or cookies
            web_cookies, web_info = await capture_web_session(
                base, web_res["code"], web_res.get("state") or web["state"], web["code_verifier"]
            )
            if not web_cookies or "PHPSESSID" not in web_cookies:
                return RefreshTokenResponseDto(success=False, message="No web session captured after login")
            session_id = web_cookies["PHPSESSID"]
            web_info = web_info or {}

            # 2) Mobile token round-trip → access/refresh tokens.
            mob = generate_oauth_url(base, auth_type="mobile")
            mob_res = await self._login(mob["auth_url"], command, cookies)
            cookies = mob_res.get("session_cookies") or cookies
            access_token, refresh_token = await exchange_code_for_tokens(
                mob_res["code"], mob["code_verifier"], base
            )

            logger.info("refresh: php=%s id=%s transid=%s token=%s",
                        bool(session_id), web_info.get("id"), web_info.get("transid"), bool(access_token))

            return RefreshTokenResponseDto(
                success=True,
                access_token=access_token,
                refresh_token=refresh_token,
                session_id=session_id,
                web_session_user_id=web_info.get("id"),
                web_session_trans_id=web_info.get("transid"),
                context_state={"cookies": cookies, "origins": []},
                message="Tokens and session refreshed successfully",
            )

        except NeedsCredentials:
            return RefreshTokenResponseDto(
                success=False,
                message="Microsoft SSO session expired. Re-authenticate via /api/authenticate/oauth/mobile/url.",
            )
        except MfaRequired as ex:
            return RefreshTokenResponseDto(
                success=False,
                message=f"MFA required: {ex}. Provide a TOTP secret or re-authenticate interactively.",
            )
        except LoginFailed as ex:
            return RefreshTokenResponseDto(success=False, message=f"Login failed: {ex}")
        except Exception as ex:
            logger.exception("Refresh failed")
            return RefreshTokenResponseDto(success=False, message=f"Refresh failed: {ex}")

    async def _login(self, authorize_url: str, command: RefreshTokenCommand, cookies):
        """Run the synchronous ms-entrance login off the event loop. Seeds the
        stored cookie jar for a silent SSO; falls back to credentials if given.
        `cookies` is always an inline list or None — never the default file."""
        return await asyncio.to_thread(
            ms_login,
            authorize_url,
            username=command.email,
            password=command.password,
            totp_secret=command.totp_secret,
            cookies=cookies,
        )


def _cookies_from_state(state: dict | None) -> list | None:
    """Pull the inline cookie list out of a stored context_state. Accepts the
    legacy Playwright storage_state shape (`{cookies: [...], origins: [...]}`)
    and tolerates a dict-of-cookies from a buggy serializer."""
    if not state:
        return None
    cookies = state.get("cookies")
    if isinstance(cookies, list):
        return cookies or None
    if isinstance(cookies, dict):
        return list(cookies.values()) or None
    return None
