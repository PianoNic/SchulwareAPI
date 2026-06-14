"""Stateless token + session refresh via Playwright.

Translated from the standalone refresher service (formerly in
SchulyPlugins/src/Schuly.Plugin.Schulware/refresher/main.py). Folded in here so
SchulwareAPI is the single Schulnetz-talking-to surface.

State contract: the caller passes `context_state` (Playwright storage_state
dict) in; we hydrate a browser context from it; on success we return the
updated state for the caller to persist. SchulwareAPI itself stores nothing.
"""

import base64
import hashlib
import os
import re
import secrets
import string

from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from playwright.async_api import async_playwright

from dataclasses import dataclass

from mediatorx import ICommand, ICommandHandler

from src.application.dtos.refresh_dtos import RefreshTokenResponseDto
from src.application.services.web_session_service import capture_web_session
from src.infrastructure.logging_config import get_logger

SCHULNETZ_CLIENT_ID = os.getenv("SCHULNETZ_CLIENT_ID", "ppyybShnMerHdtBQ")

logger = get_logger("refresh_token_command")

@dataclass
class RefreshTokenCommand(ICommand[RefreshTokenResponseDto]):
    schulnetz_base_url: str
    context_state: dict | None = None
    email: str | None = None
    password: str | None = None
    user_agent: str | None = None


class RefreshTokenHandler(ICommandHandler[RefreshTokenCommand, RefreshTokenResponseDto]):
    """Drive a one-shot browser session to harvest fresh mobile + web tokens.

    Returns the updated browser context state alongside the tokens. Caller
    persists the state and replays it on the next call.
    """

    async def handle(self, command: RefreshTokenCommand) -> RefreshTokenResponseDto:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                context_state = _normalize_state(command.context_state)
                if context_state:
                    cs_cookies = context_state.get("cookies", [])
                    cs_origins = context_state.get("origins", [])
                    domains = sorted({c.get("domain", "") for c in cs_cookies})
                    logger.info(
                        "Refresh: %d cookies across %s, %d localStorage origins",
                        len(cs_cookies), domains, len(cs_origins),
                    )

                ctx_kwargs = {}
                if context_state:
                    ctx_kwargs["storage_state"] = context_state
                if command.user_agent:
                    # MS binds session cookies to UA — caller MUST send the same UA the
                    # cookies were captured with, otherwise the SSO replay is rejected.
                    ctx_kwargs["user_agent"] = command.user_agent
                context = await browser.new_context(**ctx_kwargs)

                host = urlparse(command.schulnetz_base_url).netloc
                captured: dict[str, str | None] = {"code": None, "state": None}

                async def _harvest_code(route):
                    # Grab the OAuth code off the redirect to Schulnetz, then ABORT it.
                    # Letting the browser load /?code= makes Schulnetz consume the
                    # single-use code right there, leaving the later httpx exchange
                    # with a spent code and a dead PHPSESSID. (Same trick as the
                    # mobile-token flow in _exchange_mobile_tokens.)
                    req_url = route.request.url
                    if "code=" in req_url:
                        qs = parse_qs(urlparse(req_url).query)
                        captured["code"] = qs.get("code", [None])[0]
                        captured["state"] = qs.get("state", [None])[0]
                        await route.abort()
                    else:
                        await route.continue_()

                page = await context.new_page()
                await page.route(lambda u: host in u, _harvest_code)
                code: str | None = None
                state: str | None = None

                try:
                    try:
                        await page.goto(command.schulnetz_base_url, wait_until="load", timeout=60_000)
                    except Exception:
                        pass  # the post-SSO ?code= redirect is intercepted + aborted

                    # Expired MS SSO → need credentials to re-auth via Microsoft.
                    if not captured["code"] and "login.microsoftonline.com" in page.url:
                        if not command.email or not command.password:
                            return RefreshTokenResponseDto(
                                success=False,
                                message="Microsoft SSO session expired. Re-authenticate via /api/authenticate/oauth/mobile/url.",
                            )
                        try:
                            await _perform_microsoft_sso(page, command.email, command.password)
                        except Exception:
                            pass  # final ?code= redirect is intercepted + aborted

                    # Let the intercepted redirect settle.
                    for _ in range(20):
                        if captured["code"]:
                            break
                        await page.wait_for_timeout(500)

                    code, state = captured["code"], captured["state"]
                    if not code:
                        return RefreshTokenResponseDto(success=False, message="Failed to obtain authorization code")

                finally:
                    await page.close()

                # Mobile token exchange via a separate PKCE round-trip.
                access_token, refresh_token = await _exchange_mobile_tokens(context, command.schulnetz_base_url)

                # Capture web session cookies + landing-page params using the original code.
                session_id, web_user_id, web_trans_id = await _capture_web_session(
                    command.schulnetz_base_url, code, state
                )

                # Snapshot the updated context for the caller to persist.
                updated_state = await context.storage_state()

                return RefreshTokenResponseDto(
                    success=True,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    session_id=session_id,
                    web_session_user_id=web_user_id,
                    web_session_trans_id=web_trans_id,
                    context_state=updated_state,
                    message="Tokens and session refreshed successfully",
                )

            except Exception as ex:
                logger.exception("Refresh failed")
                return RefreshTokenResponseDto(success=False, message=f"Refresh failed: {ex}")
            finally:
                await browser.close()

# ---------- internals ----------

def _normalize_state(state: dict | None) -> dict | None:
    """Coerce a context_state into the shape Playwright's storage_state expects.

    Playwright requires `cookies` and `origins` to be arrays. A buggy caller may
    persist them as objects/dicts (e.g. a keyed map, or arrays mangled into `{}`
    by a serializer that can't handle the value type). When we get a dict, fall
    back to its values; anything else non-list becomes an empty list so
    `new_context` never rejects the shape.
    """
    if not state:
        return state

    def as_list(value):
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return list(value.values())
        return []

    return {**state, "cookies": as_list(state.get("cookies")), "origins": as_list(state.get("origins"))}


async def _perform_microsoft_sso(page, email: str, password: str) -> None:
    email_input = 'input[type="email"], input[name="loginfmt"]'
    await page.wait_for_selector(email_input, timeout=10_000)
    await page.fill(email_input, email)
    await page.click("#idSIButton9")

    password_input = 'input[type="password"], input[name="passwd"]'
    await page.wait_for_selector(password_input, timeout=10_000)
    await page.fill(password_input, password)
    await page.click("#idSIButton9")

    # "Stay signed in?" prompt is best-effort.
    try:
        stay = page.locator("#idSIButton9")
        await stay.wait_for(state="visible", timeout=5_000)
        await stay.click()
    except Exception:
        pass

def _extract_code_state(url: str) -> tuple[str | None, str | None]:
    if "code=" not in url:
        return None, None
    qs = parse_qs(urlparse(url).query)
    return qs.get("code", [None])[0], qs.get("state", [None])[0]

async def _exchange_mobile_tokens(context, schulnetz_base_url: str) -> tuple[str | None, str | None]:
    """Run a fresh PKCE flow inside the same context to mint mobile tokens."""
    code_verifier = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(128))
    s256 = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(s256).decode().rstrip("=")

    auth_params = {
        "response_type": "code",
        "client_id": SCHULNETZ_CLIENT_ID,
        "state": secrets.token_hex(16),
        "redirect_uri": "",
        "scope": "openid ",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "nonce": secrets.token_hex(16),
    }

    page = await context.new_page()
    pkce_code: str | None = None
    try:
        captured = {"code": None}

        async def intercept(route):
            url = route.request.url
            if "code=" in url:
                captured["code"] = parse_qs(urlparse(url).query).get("code", [None])[0]
            await route.abort()

        await page.route("**/schulnetz.web.app/**", intercept)
        await page.route("**/callback*code=*", intercept)

        auth_url = f"{schulnetz_base_url}/authorize.php?{urlencode(auth_params)}"
        try:
            await page.goto(auth_url, wait_until="load", timeout=30_000)
        except Exception:
            pass

        pkce_code = captured["code"]
        if not pkce_code and "code=" in page.url:
            pkce_code = parse_qs(urlparse(page.url).query).get("code", [None])[0]
    finally:
        await page.close()

    if not pkce_code:
        return None, None

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{schulnetz_base_url}/token.php",
            data={
                "grant_type": "authorization_code",
                "code": pkce_code,
                "redirect_uri": "",
                "code_verifier": code_verifier,
                "client_id": SCHULNETZ_CLIENT_ID,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if res.status_code != 200:
            return None, None
        data = res.json()
        return data.get("access_token"), data.get("refresh_token")

async def _capture_web_session(
    schulnetz_base_url: str, code: str, state: str | None
) -> tuple[str | None, str | None, str | None]:
    # Delegate to the canonical capture: it exchanges the code at the school root
    # `/` (NOT /loginto.php, which returns a "session expired" page) and uses
    # WEB_HEADERS — so the refresh path mints a session identically to the initial
    # OAuth capture, and the scraper's UA matches.
    cookies, info = await capture_web_session(schulnetz_base_url, code, state or "")
    if not cookies:
        return None, None, None
    info = info or {}
    return cookies.get("PHPSESSID"), info.get("id"), info.get("transid")

