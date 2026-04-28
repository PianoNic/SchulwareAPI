import httpx
import re
from typing import Optional, Dict, Tuple
from urllib.parse import urljoin, urlencode
from bs4 import BeautifulSoup
from src.infrastructure.logging_config import get_logger

logger = get_logger("web_session")

WEB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
}


async def capture_web_session(schulnetz_base_url: str, code: str, state: str) -> Tuple[Optional[Dict[str, str]], Optional[Dict[str, str]]]:
    """
    Exchange an OAuth authorization code for a Schulnetz PHP web session.

    Uses loginto.php (the actual Schulnetz callback endpoint) to exchange
    the OAuth code for a PHPSESSID cookie. Pure HTTP, no browser needed.

    Args:
        schulnetz_base_url: e.g. https://schulnetz.bbbaden.ch
        code: OAuth authorization code from Microsoft SSO
        state: OAuth state parameter

    Returns:
        Tuple of (cookies_dict, session_info) or (None, None) if failed.
        session_info contains: id, transid, navigation_urls extracted from the landing page.
    """
    login_url = f"{schulnetz_base_url}/loginto.php"
    params = {"code": code, "state": state, "mode": "4", "lang": ""}

    logger.info(f"Exchanging OAuth code for web session via loginto.php")
    logger.info(f"Code length: {len(code)}, State: {state[:20]}...")

    async with httpx.AsyncClient(headers=WEB_HEADERS, follow_redirects=True, timeout=30.0) as client:
        try:
            response = await client.get(login_url, params=params)

            cookies = {}
            for resp in response.history + [response]:
                cookies.update(dict(resp.cookies))

            logger.info(f"Final status: {response.status_code}, URL: {response.url}")
            logger.info(f"Cookies captured: {list(cookies.keys())}")

            if "PHPSESSID" not in cookies:
                logger.warning("No PHPSESSID captured — login may have failed")
                return None, None

            session_info = _extract_session_info(str(response.url), response.text)

            logger.info(f"Session captured. PHPSESSID: {cookies['PHPSESSID'][:20]}...")
            if session_info:
                logger.info(f"Session id: {session_info.get('id')}, pages: {len(session_info.get('navigation_urls', {}))}")

            return cookies, session_info

        except Exception as e:
            logger.error(f"Failed to capture web session: {e}")
            return None, None


def _extract_session_info(url: str, html: str) -> Optional[Dict[str, str]]:
    """Extract session-specific parameters (id, transid) and navigation URLs from the landing page."""
    info = {}

    id_match = re.search(r'[?&]id=([a-f0-9]+)', url)
    if id_match:
        info["id"] = id_match.group(1)

    transid_match = re.search(r'[?&]transid=([a-f0-9]+)', url)
    if transid_match:
        info["transid"] = transid_match.group(1)

    if not html:
        return info if info else None

    soup = BeautifulSoup(html, "html.parser")

    navigation_urls = {}
    for link in soup.select("a[href*='pageid']"):
        href = link.get("href", "")
        text = link.get_text(strip=True)
        if text and "pageid=" in href:
            navigation_urls[text] = href

    if navigation_urls:
        info["navigation_urls"] = navigation_urls

    if not info.get("id"):
        id_match = re.search(r'[?&]id=([a-f0-9]+)', html)
        if id_match:
            info["id"] = id_match.group(1)

    return info if info else None


async def scrape_page(schulnetz_base_url: str, cookies: Dict[str, str], pageid: str, session_id: str, transid: str) -> Optional[str]:
    """
    Fetch a Schulnetz page using stored session cookies.

    Args:
        schulnetz_base_url: e.g. https://schulnetz.bbbaden.ch
        cookies: Session cookies (must include PHPSESSID)
        pageid: The page identifier (e.g. "21311" for grades)
        session_id: The session id parameter from the URL
        transid: The transaction id parameter

    Returns:
        HTML content or None if session expired
    """
    url = f"{schulnetz_base_url}/index.php"
    params = {"pageid": pageid, "id": session_id, "transid": transid}

    headers = {
        **WEB_HEADERS,
        "Referer": f"{schulnetz_base_url}/",
        "Sec-Fetch-Site": "same-origin",
    }

    async with httpx.AsyncClient(headers=headers, cookies=cookies, follow_redirects=True, timeout=30.0) as client:
        try:
            response = await client.get(url, params=params)

            if response.status_code == 200:
                if "login.microsoftonline.com" in str(response.url):
                    logger.warning("Session expired — redirected to Microsoft login")
                    return None
                return response.text

            logger.warning(f"Unexpected status {response.status_code} for pageid={pageid}")
            return None

        except Exception as e:
            logger.error(f"Failed to scrape pageid={pageid}: {e}")
            return None


async def validate_session(schulnetz_base_url: str, cookies: Dict[str, str], session_id: str, transid: str) -> bool:
    """Check if a PHP session is still valid."""
    html = await scrape_page(schulnetz_base_url, cookies, "21111", session_id, transid)
    if html is None:
        return False
    return "pageid" in html


# Page ID constants for known Schulnetz pages
PAGE_IDS = {
    "home": "21111",
    "absences": "21119",
    "agenda": "21200",
    "grades": "21311",
    "lessons": "21355",
    "schedule": "22202",
    "student_id": "24030",
}
