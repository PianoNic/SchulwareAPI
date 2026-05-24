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
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from playwright.async_api import async_playwright

from src.application.dtos.refresh_dtos import RefreshTokenRequestDto, RefreshTokenResponseDto
from src.infrastructure.logging_config import get_logger

SCHULNETZ_CLIENT_ID = os.getenv("SCHULNETZ_CLIENT_ID", "ppyybShnMerHdtBQ")

logger = get_logger("refresh_token_command")


async def refresh_token_command_async(request: RefreshTokenRequestDto) -> RefreshTokenResponseDto:
    """Drive a one-shot browser session to harvest fresh mobile + web tokens.

    Returns the updated browser context state alongside the tokens. Caller
    persists the state and replays it on the next call.
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            if request.context_state:
                cs_cookies = request.context_state.get("cookies", [])
                domains = sorted({c.get("domain", "") for c in cs_cookies})
                logger.info("Refresh with context_state: %d cookies across domains %s", len(cs_cookies), domains)
            else:
                logger.info("Refresh with NO context_state (cold start)")

            context = (
                await browser.new_context(storage_state=request.context_state)
                if request.context_state
                else await browser.new_context()
            )

            page = await context.new_page()
            code: Optional[str] = None
            state: Optional[str] = None

            try:
                await page.goto(request.schulnetz_base_url, wait_until="load", timeout=60_000)
                current_url = page.url
                logger.info("After initial navigation, URL is: %s", current_url)

                # SSO session expired → need credentials to re-auth via Microsoft.
                if "login.microsoftonline.com" in current_url:
                    if not request.email or not request.password:
                        return RefreshTokenResponseDto(
                            success=False,
                            message="Microsoft SSO session expired. Email and password required for re-authentication.",
                        )
                    await _perform_microsoft_sso(page, request)
                    await page.wait_for_url(f"{request.schulnetz_base_url}*", timeout=30_000)

                current_url = page.url
                code, state = _extract_code_state(current_url)

                # Some Schulnetz instances need a second hit before the code shows up.
                if not code:
                    await page.goto(request.schulnetz_base_url, wait_until="load", timeout=30_000)
                    code, state = _extract_code_state(page.url)

                if not code:
                    return RefreshTokenResponseDto(success=False, message="Failed to obtain authorization code")

            finally:
                await page.close()

            # Mobile token exchange via a separate PKCE round-trip.
            access_token, refresh_token = await _exchange_mobile_tokens(context, request.schulnetz_base_url)

            # Capture web session cookies + landing-page params using the original code.
            session_id, web_user_id, web_trans_id = await _capture_web_session(
                request.schulnetz_base_url, code, state
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

async def _perform_microsoft_sso(page, request: RefreshTokenRequestDto) -> None:
    email_input = 'input[type="email"], input[name="loginfmt"]'
    await page.wait_for_selector(email_input, timeout=10_000)
    await page.fill(email_input, request.email)
    await page.click("#idSIButton9")

    password_input = 'input[type="password"], input[name="passwd"]'
    await page.wait_for_selector(password_input, timeout=10_000)
    await page.fill(password_input, request.password)
    await page.click("#idSIButton9")

    # "Stay signed in?" prompt is best-effort.
    try:
        stay = page.locator("#idSIButton9")
        await stay.wait_for(state="visible", timeout=5_000)
        await stay.click()
    except Exception:
        pass


def _extract_code_state(url: str) -> tuple[Optional[str], Optional[str]]:
    if "code=" not in url:
        return None, None
    qs = parse_qs(urlparse(url).query)
    return qs.get("code", [None])[0], qs.get("state", [None])[0]


async def _exchange_mobile_tokens(context, schulnetz_base_url: str) -> tuple[Optional[str], Optional[str]]:
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
    pkce_code: Optional[str] = None
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
    schulnetz_base_url: str, code: str, state: Optional[str]
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        login_url = f"{schulnetz_base_url}/loginto.php"
        params = {"code": code, "state": state or "", "mode": "4", "lang": ""}
        res = await client.get(login_url, params=params)

        cookies: dict[str, str] = {}
        for resp in res.history + [res]:
            cookies.update(dict(resp.cookies))

        session_id = cookies.get("PHPSESSID")

        html = res.text
        id_match = re.search(r"[?&]id=([a-f0-9]{10,})", html)
        transid_match = re.search(r"[?&]transid=([a-f0-9]+)", html)
        web_user_id = id_match.group(1) if id_match else None
        web_trans_id = transid_match.group(1) if transid_match else None

        return session_id, web_user_id, web_trans_id


