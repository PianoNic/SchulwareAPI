"""Schulnetz's own (non-Microsoft) login, over plain HTTP.

Schools without Microsoft sign-in show a form on `authorize.php` / `loginto.php` with a
hidden `loginhash` plus `login` and `passwort`, optionally followed by a `pin` form for
2FA. The mobile leg ends at a redirect carrying the OAuth `code`; the web leg ends on the
dashboard, whose links carry `id` / `transid`.
"""

from collections.abc import Callable
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from entrance import totp_now

from src.api.auth.auth import exchange_code_for_tokens, generate_oauth_url
from src.application.services.web_session_service import WEB_HEADERS, _extract_session_info
from src.infrastructure.logging_config import get_logger

logger = get_logger("native_login")

MAX_HOPS = 10
MICROSOFT_HOST = "login.microsoftonline.com"


class NativeLoginFailed(Exception):
    pass


def totp_code_for(secret: str | None, code: str | None) -> str | None:
    """The 2FA code to send: an explicit code wins, else one generated from a Base32 secret or otpauth:// URI."""
    if code:
        return code.strip()
    if not secret:
        return None
    if secret.lower().startswith("otpauth://"):
        secret = parse_qs(urlparse(secret).query).get("secret", [""])[0]
    return totp_now(secret.replace(" ", "").upper())


def _client(user_agent: str | None, transport: httpx.AsyncBaseTransport | None) -> httpx.AsyncClient:
    headers = {**WEB_HEADERS, **({"User-Agent": user_agent} if user_agent else {})}
    return httpx.AsyncClient(headers=headers, follow_redirects=False, timeout=30.0, transport=transport)


async def detect_login_mode(base_url: str, user_agent: str | None = None, transport: httpx.AsyncBaseTransport | None = None) -> str:
    """'native' when authorize.php shows Schulnetz's own login form, otherwise 'microsoft'."""
    auth = generate_oauth_url(base_url, auth_type="mobile")
    async with _client(user_agent, transport) as client:
        response = await client.get(auth["auth_url"])
        for _ in range(MAX_HOPS):
            if not response.is_redirect:
                break
            location = response.headers.get("location", "")
            if MICROSOFT_HOST in location:
                return "microsoft"
            response = await client.get(urljoin(str(response.url), location))
    return "native" if _form_with(response.text, "passwort") is not None else "microsoft"


async def native_mobile_tokens(base_url: str, email: str, password: str, totp: str | None, user_agent: str | None = None, transport: httpx.AsyncBaseTransport | None = None) -> tuple[str, str | None]:
    """Log in on Schulnetz's own form and exchange the resulting code for mobile tokens."""
    auth = generate_oauth_url(base_url, auth_type="mobile")
    async with _client(user_agent, transport) as client:
        first = await client.get(auth["auth_url"])
        final = await _submit_forms(client, first, email, password, totp, stop=_carries_code)

    code = _code_from(final)
    if not code:
        raise NativeLoginFailed("Schulnetz did not return an authorization code")
    access_token, refresh_token = await exchange_code_for_tokens(code, auth["code_verifier"], base_url)
    if not access_token:
        raise NativeLoginFailed("Schulnetz refused the authorization code")
    return access_token, refresh_token


async def native_web_session(base_url: str, email: str, password: str, totp: str | None, user_agent: str | None = None, transport: httpx.AsyncBaseTransport | None = None) -> tuple[dict[str, str], dict]:
    """Log in through loginto.php and return the PHP session cookies plus id / transid."""
    async with _client(user_agent, transport) as client:
        first = await client.get(f"{base_url.rstrip('/')}/loginto.php")
        final = await _submit_forms(client, first, email, password, totp, stop=lambda _: False)
        cookies = {cookie.name: cookie.value for cookie in client.cookies.jar}

    info = _extract_session_info(str(final.url), final.text) or {}
    if "PHPSESSID" not in cookies or not info.get("id") or not info.get("transid"):
        raise NativeLoginFailed("Signed in, but Schulnetz opened no web session")
    return cookies, info


async def _submit_forms(client: httpx.AsyncClient, response: httpx.Response, email: str, password: str, totp: str | None, stop: Callable[[httpx.Response], bool]) -> httpx.Response:
    """Follow redirects and fill the login and 2FA forms until `stop` holds or no form is left."""
    sent_login = sent_pin = False
    for _ in range(MAX_HOPS):
        if stop(response):
            return response
        if response.is_redirect:
            response = await client.get(urljoin(str(response.url), response.headers.get("location", "")))
            continue

        html = response.text
        if (form := _form_with(html, "passwort")) is not None:
            if sent_login:
                raise NativeLoginFailed(_error_text(html))
            data = {**_fields(form), "login": email, "passwort": password}
            sent_login = True
        elif (form := _form_with(html, "pin")) is not None:
            if sent_pin:
                raise NativeLoginFailed("Schulnetz rejected the 2FA code")
            if totp is None:
                raise NativeLoginFailed("This account uses 2FA; provide a TOTP secret")
            data = {**_fields(form), "pin": totp}
            sent_pin = True
        else:
            return response

        action = urljoin(str(response.url), form.get("action") or str(response.url))
        if (form.get("method") or "post").lower() == "get":
            response = await client.get(action, params=data)
        else:
            # Encoded by hand: httpx 0.28's AsyncClient won't send a `data=` form body.
            response = await client.post(action, content=urlencode(data), headers={"Content-Type": "application/x-www-form-urlencoded"})
    raise NativeLoginFailed("Too many redirects during the Schulnetz login")


def _form_with(html: str, field: str):
    soup = BeautifulSoup(html or "", "html.parser")
    for form in soup.find_all("form"):
        if form.find("input", attrs={"name": field}) is not None:
            return form
    return None


def _fields(form) -> dict[str, str]:
    fields = {}
    for field in form.find_all("input"):
        name = field.get("name")
        kind = (field.get("type") or "text").lower()
        if not name or kind in ("submit", "button", "image") or (kind in ("checkbox", "radio") and not field.has_attr("checked")):
            continue
        fields[name] = field.get("value", "")
    return fields


def _error_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for element in soup.select('[style*="#ffb138"], .error, .alert, .mdl-color-text--red'):
        text = element.get_text(" ", strip=True)
        if text:
            return text[:300]
    return "Schulnetz rejected the email or password"


def _location(response: httpx.Response) -> str:
    return response.headers.get("location", "") if response.is_redirect else str(response.url)


def _carries_code(response: httpx.Response) -> bool:
    return "code" in parse_qs(urlparse(_location(response)).query)


def _code_from(response: httpx.Response) -> str | None:
    return parse_qs(urlparse(_location(response)).query).get("code", [None])[0]
