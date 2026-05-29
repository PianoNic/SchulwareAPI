import httpx
import re

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

async def capture_web_session(
    schulnetz_base_url: str,
    code: str,
    state: str,
    code_verifier: str | None = None,
) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    """
    Exchange an OAuth authorization code for a Schulnetz PHP web session.

    Uses loginto.php (the actual Schulnetz callback endpoint) to exchange
    the OAuth code for a PHPSESSID cookie. Pure HTTP, no browser needed.

    Args:
        schulnetz_base_url: e.g. https://schulnetz.bbbaden.ch
        code: OAuth authorization code from Microsoft SSO
        state: OAuth state parameter
        code_verifier: PKCE code_verifier (required if authorize.php was called with code_challenge)

    Returns:
        Tuple of (cookies_dict, session_info) or (None, None) if failed.
        session_info contains: id, transid, navigation_urls extracted from the landing page.
    """
    # Schulnetz's OAuth callback is the school root (`/`), NOT `/loginto.php`.
    # The root handler exchanges the code with Microsoft, sets PHPSESSID, and
    # then redirects internally to /loginto.php?mode=4&lang= which renders the
    # dashboard. Hitting /loginto.php?code=... directly returns a
    # "session expired" error page.
    login_url = f"{schulnetz_base_url}/"
    params: dict[str, str] = {"code": code, "state": state}
    if code_verifier:
        params["code_verifier"] = code_verifier

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

def _extract_session_info(url: str, html: str) -> dict[str, str] | None:
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

async def scrape_page(
    schulnetz_base_url: str,
    cookies: dict[str, str],
    pageid: str,
    session_id: str,
    transid: str,
    user_agent: str | None = None,
    additional_cookies: list[dict[str, str]] | None = None,
) -> tuple[str | None, str | None, str | None]:
    """
    Fetch a Schulnetz page using stored session cookies.

    Args:
        schulnetz_base_url: e.g. https://schulnetz.bbbaden.ch
        cookies: Session cookies (must include PHPSESSID)
        pageid: The page identifier (e.g. "21311" for grades)
        session_id: The session id parameter from the URL
        transid: The transaction id parameter
        user_agent: Override the default UA. Schulnetz binds PHPSESSID to the UA
            that created the session, so callers replaying a WebView-issued
            session MUST pass the WebView's UA.

    Returns:
        Tuple of (html, refreshed_id, refreshed_transid). `html` is None when the
        session is no longer valid. The refreshed id/transid come from the
        navigation links in the response and rotate per-request on some
        instances (e.g. bs-aarau treats `transid` as a one-shot CSRF nonce —
        reusing the same value yields a login redirect on the next call).
        Callers should persist the refreshed values and use them on the next
        request. Returns (None, None, None) on expired session or error.
    """
    url = f"{schulnetz_base_url}/index.php"
    params = {"pageid": pageid, "id": session_id, "transid": transid}

    headers = {
        **WEB_HEADERS,
        "Referer": f"{schulnetz_base_url}/",
        "Sec-Fetch-Site": "same-origin",
    }
    if user_agent:
        headers["User-Agent"] = user_agent

    # Hydrate the cookie jar with the Schulnetz cookies on the school host plus
    # any additional cookies the caller supplies (typically Microsoft SSO
    # cookies from the captured `context_state`). Some instances (e.g.
    # bs-aarau) lean on Microsoft's silent-SSO `/reprocess` endpoint to mint a
    # fresh OAuth code mid-flight when PHPSESSID gets shaky; without those MS
    # cookies the redirect chain dead-ends at the login form.
    jar = httpx.Cookies()
    schulnetz_host = httpx.URL(schulnetz_base_url).host
    for name, value in cookies.items():
        jar.set(name, value, domain=schulnetz_host)
    extra_by_domain: dict[str, list[str]] = {}
    if additional_cookies:
        for c in additional_cookies:
            name = c.get("name")
            value = c.get("value")
            domain = c.get("domain") or ""
            if not name or value is None:
                continue
            normalized = domain.lstrip(".")
            jar.set(name, value, domain=normalized)
            extra_by_domain.setdefault(normalized, []).append(name)
    if extra_by_domain:
        summary = ", ".join(f"{d}: {len(n)}" for d, n in extra_by_domain.items())
        logger.info(f"Forwarding additional cookies — {summary}")
    else:
        logger.info("No additional_cookies forwarded on this request")

    async with httpx.AsyncClient(headers=headers, cookies=jar, follow_redirects=True, timeout=30.0) as client:
        try:
            response = await client.get(url, params=params)

            if response.status_code == 200:
                final_url = str(response.url)
                # Schulnetz instances differ in how they signal an expired session:
                # bbbaden bounces straight to login.microsoftonline.com, but bs-aarau
                # first lands on /loginto.php?mode=7 (its own "please log in" page)
                # and only then to Microsoft. Both indicate the cookies are no
                # longer authenticated.
                if "login.microsoftonline.com" in final_url or "/loginto.php" in final_url:
                    logger.warning(f"Session expired — redirected to {final_url}")
                    return None, None, None
                refreshed_id, refreshed_transid = _extract_refreshed_session(response.text)
                return response.text, refreshed_id, refreshed_transid

            logger.warning(f"Unexpected status {response.status_code} for pageid={pageid}")
            return None, None, None

        except Exception as e:
            logger.error(f"Failed to scrape pageid={pageid}: {e}")
            return None, None, None


def _extract_refreshed_session(html: str) -> tuple[str | None, str | None]:
    """Pull a fresh (id, transid) pair from any pageid nav link in the response."""
    if not html:
        return None, None
    match = re.search(r'href="[^"]*[?&]id=([a-f0-9]+)[^"]*[?&]transid=([a-f0-9]+)', html)
    if match:
        return match.group(1), match.group(2)
    id_match = re.search(r'[?&]id=([a-f0-9]+)', html)
    transid_match = re.search(r'[?&]transid=([a-f0-9]+)', html)
    return (
        id_match.group(1) if id_match else None,
        transid_match.group(1) if transid_match else None,
    )

async def validate_session(
    schulnetz_base_url: str,
    cookies: dict[str, str],
    session_id: str,
    transid: str,
    user_agent: str | None = None,
    additional_cookies: list[dict[str, str]] | None = None,
) -> tuple[bool, str | None, str | None]:
    """Check if a PHP session is still valid.

    Returns (is_valid, refreshed_id, refreshed_transid). The id/transid come
    from nav links on the response page; on Schulnetz instances that rotate
    `transid` per-request, the caller MUST use the refreshed values for the
    next call or the session will appear to die after one request.

    `scrape_page` already returns None when the request is bounced to a login
    page (Microsoft or `/loginto.php`), so a non-None response is sufficient to
    consider the session live.
    """
    html, refreshed_id, refreshed_transid = await scrape_page(
        schulnetz_base_url,
        cookies,
        "21111",
        session_id,
        transid,
        user_agent=user_agent,
        additional_cookies=additional_cookies,
    )
    return html is not None, refreshed_id, refreshed_transid

async def fetch_scheduler_data(schulnetz_base_url: str, cookies: dict[str, str], session_id: str, transid: str, date: str | None = None, user_agent: str | None = None) -> str | None:
    """Fetch timetable/agenda data from the scheduler AJAX endpoint."""
    from datetime import datetime, timedelta

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    dt = datetime.strptime(date, "%Y-%m-%d")
    week_start = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
    week_end = (dt + timedelta(days=6 - dt.weekday())).strftime("%Y-%m-%d")

    url = f"{schulnetz_base_url}/scheduler_processor.php"
    params = {
        "view": "week",
        "curr_date": date,
        "min_date": week_start,
        "max_date": week_end,
        "ansicht": "schueleransicht",
        "id": session_id,
        "transid": transid,
        "pageid": "22202",
        "timeshift": "-120",
    }

    headers = {
        **WEB_HEADERS,
        "Referer": f"{schulnetz_base_url}/",
        "Sec-Fetch-Site": "same-origin",
        "Accept": "text/html, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }
    if user_agent:
        headers["User-Agent"] = user_agent

    async with httpx.AsyncClient(headers=headers, cookies=cookies, follow_redirects=True, timeout=30.0) as client:
        try:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                return response.text
            logger.warning(f"Scheduler returned {response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch scheduler data: {e}")
            return None

# Page ID constants for known Schulnetz pages
PAGE_IDS = {
    "home": "1",
    "absences": "21111",
    "agenda": "21200",
    "grades": "21311",
    "lessons": "21355",
    "schedule": "22202",
    "documents": "24030",
    "student_id": "50505",
}
