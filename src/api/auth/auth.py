"""Schulnetz OAuth helpers (pure HTTP).

Builds Schulnetz's PKCE authorize URL and exchanges the resulting authorization
code for mobile tokens at `/token.php`. The browserless Microsoft Entra login
that walks `authorize.php → login.microsoftonline.com → callback` is handled by
the `ms-entrance` package (see `refresh_token_command`); this module no longer
drives a browser.
"""

import base64
import hashlib
import os
import secrets
import string
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from src.application.constants import DEFAULT_SCHULNETZ_CLIENT_ID
from src.infrastructure.logging_config import get_logger

logger = get_logger("authentication")

load_dotenv()

# Public, instance-invariant default; override via env only for a non-standard deployment.
SCHULNETZ_CLIENT_ID = os.getenv("SCHULNETZ_CLIENT_ID", DEFAULT_SCHULNETZ_CLIENT_ID)


def generate_random_string(length: int) -> str:
    """Generate a cryptographically secure random string."""
    return "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(length)
    )


def generate_pkce_challenge() -> tuple[str, str]:
    """Generate PKCE code verifier and code challenge."""
    code_verifier = generate_random_string(128)
    s256 = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = (base64.urlsafe_b64encode(s256).decode("utf-8").rstrip("="))
    return code_verifier, code_challenge


def generate_auth_params(state: str, code_challenge: str, nonce: str) -> dict[str, str]:
    """Generate OAuth2 authorization parameters."""
    return {
        "response_type": "code",
        "client_id": SCHULNETZ_CLIENT_ID,
        "state": state,
        "redirect_uri": "",  # Empty as shown in curl commands
        "scope": "openid ",  # Note the trailing space as in curl
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "nonce": nonce,
    }


def extract_auth_code_from_url(url: str) -> tuple[str | None, str | None]:
    """Extract authorization code and state from URL parameters."""
    if "code=" not in url:
        return None, None

    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query, keep_blank_values=True)
        auth_code = query_params.get("code", [None])[0]
        received_state = query_params.get("state", [None])[0]

        if auth_code:
            logger.info(f"Extracted auth code: {auth_code[:50]}... (length: {len(auth_code)})")
        if received_state:
            logger.info(f"Extracted state: {received_state[:50]}... (length: {len(received_state)})")

        return auth_code, received_state
    except Exception as e:
        logger.error(f"Error extracting auth code from URL: {e}")
        return None, None


async def exchange_code_for_tokens(auth_code: str, code_verifier: str, base_url: str) -> tuple[str | None, str | None]:
    """
    Exchange authorization code for access and refresh tokens.

    Args:
        auth_code: Authorization code obtained from Microsoft
        code_verifier: PKCE code verifier used in the initial request
        base_url: Base URL of the target Schulnetz instance (e.g. https://schulnetz.bbbaden.ch)

    Returns:
        Tuple of (access_token, refresh_token) or (None, None) if failed
    """
    if not base_url:
        raise ValueError("base_url is required for exchange_code_for_tokens")
    httpx_client = httpx.AsyncClient(
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "Upgrade-Insecure-Requests": "1",
        },
    )

    token_url = f"{base_url.rstrip('/')}/token.php"
    token_data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": "",  # Must match the one used throughout the flow (empty in curl commands)
        "code_verifier": code_verifier,
        "client_id": SCHULNETZ_CLIENT_ID,
    }

    # Set headers for the token exchange request to match the working curl command exactly
    headers_for_token_exchange = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://schulnetz.web.app/",
        "sec-ch-ua": '"Opera";v="120", "Not-A.Brand";v="8", "Chromium";v="135"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    logger.info("Exchanging authorization code for tokens...")
    logger.info(f"Token exchange URL: {token_url}")

    try:
        token_response = await httpx_client.post(
            token_url, data=token_data, headers=headers_for_token_exchange
        )
        token_response.raise_for_status()
        token_json = token_response.json()

        access_token = token_json.get("access_token")
        refresh_token = token_json.get("refresh_token")

        if access_token:
            logger.info("Token exchange successful")
            return access_token, refresh_token
        else:
            logger.error("Access token not found in response")
            return None, None

    except httpx.RequestError as e:
        logger.error(f"HTTP error during token exchange: {e}")
        return None, None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP Status Error during token exchange: {e.response.status_code} - {e.response.text}")
        return None, None
    finally:
        await httpx_client.aclose()


def validate_state_parameter(expected_state: str, received_state: str | None) -> bool:
    """Validate OAuth2 state parameter for CSRF protection."""
    if not received_state:
        logger.info("Note: State validation skipped - no state received")
        return False

    # Direct match - ideal case
    if received_state == expected_state:
        logger.info("State validation passed (direct match).")
        return True

    # Handle Microsoft's composite state format: {hash}{base64_encoded_original_params}
    try:
        if len(received_state) > 64:  # Longer than a typical hash
            for split_point in range(32, min(64, len(received_state))):
                potential_b64 = received_state[split_point:]
                try:
                    decoded = base64.b64decode(potential_b64, validate=True).decode("utf-8")
                    if "state=" in decoded:
                        params = parse_qs(decoded)
                        extracted_state = params.get("state", [None])[0]
                        if extracted_state == expected_state:
                            logger.info("State validation passed (extracted from Microsoft composite format).")
                            return True
                except Exception:
                    continue
    except Exception as e:
        logger.debug(f"Error parsing composite state: {e}")

    logger.warning("WARNING: State mismatch!")
    return False


def generate_oauth_url(base_url: str, auth_type: str = "mobile", redirect_uri: str = "") -> dict[str, str]:
    """
    Generate OAuth authorization URL for Microsoft login.

    Args:
        base_url: Base URL of the target Schulnetz instance (e.g. https://schulnetz.bbbaden.ch)
        auth_type: Type of authentication - "mobile" or "web"
        redirect_uri: Redirect URI for OAuth callback (empty string for Schulnetz default)

    Returns:
        Dictionary containing:
        - auth_url: The authorization URL to redirect to
        - code_verifier: PKCE code verifier (client must store this)
        - state: The state parameter for CSRF protection
    """
    if not base_url:
        raise ValueError("base_url is required for generate_oauth_url")
    # Schulnetz requires PKCE on both mobile and web flows — the authorize.php
    # endpoint rejects requests that don't include a code_challenge.
    code_verifier, code_challenge = generate_pkce_challenge()
    state = generate_random_string(32)
    nonce = generate_random_string(32)

    auth_params = {
        "response_type": "code",
        "client_id": SCHULNETZ_CLIENT_ID,
        "state": state,
        "redirect_uri": redirect_uri,
        "scope": "openid ",  # trailing space matches the original Schulnetz flow
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    auth_url = f"{base_url.rstrip('/')}/authorize.php?" + urlencode(auth_params)

    logger.info(f"Generated OAuth URL for {auth_type} authentication")

    return {
        "auth_url": auth_url,
        "state": state,
        "code_verifier": code_verifier,
    }


def extract_navigation_urls(html_content: str) -> dict:
    """
    Extract navigation URLs from the schulnetz main page HTML.

    Args:
        html_content: HTML content of the main page

    Returns:
        Dictionary mapping menu names to their URLs
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        navigation_urls = {}
        nav_menu = soup.find("nav", {"id": "nav-main-menu"})
        if not nav_menu:
            logger.warning("Could not find main navigation menu in HTML")
            return navigation_urls

        nav_links = nav_menu.find_all("a", class_="mdl-navigation__link")
        for link in nav_links:
            href = link.get("href", "")
            title_div = link.find("div", class_="cls-page--mainmenu-subtitle")
            if title_div:
                menu_name = title_div.get_text(strip=True)
            else:
                menu_name = link.get("aria-label", link.text.strip())
            navigation_urls[menu_name] = href

        logger.info(f"Successfully extracted {len(navigation_urls)} navigation URLs")
        return navigation_urls

    except Exception as e:
        logger.error(f"Error parsing HTML for navigation URLs: {e}")
        return {}
