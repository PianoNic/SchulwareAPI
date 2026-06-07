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

async def scrape_page(schulnetz_base_url: str, cookies: dict[str, str], pageid: str, session_id: str, transid: str, user_agent: str | None = None) -> str | None:
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
        HTML content or None if session expired
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

def _filename_from_disposition(disposition: str | None, fallback: str) -> str:
    """Pull the filename out of a Content-Disposition header, else use fallback."""
    if not disposition:
        return fallback
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', disposition)
    return m.group(1).strip() if m else fallback


async def download_file(
    schulnetz_base_url: str,
    cookies: dict[str, str],
    download_url: str,
    user_agent: str | None = None,
) -> tuple[bytes, str, str] | None:
    """Fetch a filestore document's raw bytes using the stored web session.

    Args:
        schulnetz_base_url: e.g. https://schulnetz.bbbaden.ch
        cookies: Session cookies (must include PHPSESSID)
        download_url: The relative export link from the documents scrape, e.g.
            "index.php?pageid=10051&tblName=tblFilestore&listindex=1&id=..&transid=.."
        user_agent: UA the PHPSESSID was created with (Schulnetz binds to it).

    Returns:
        (content, content_type, filename) or None if the session expired / failed.
    """
    url = f"{schulnetz_base_url}/{download_url.lstrip('/')}"
    headers = {
        **WEB_HEADERS,
        "Referer": f"{schulnetz_base_url}/",
        "Sec-Fetch-Site": "same-origin",
    }
    if user_agent:
        headers["User-Agent"] = user_agent

    async with httpx.AsyncClient(headers=headers, cookies=cookies, follow_redirects=True, timeout=60.0) as client:
        try:
            response = await client.get(url)
            if response.status_code != 200 or "login.microsoftonline.com" in str(response.url):
                logger.warning(f"Download failed (status {response.status_code}) for {url}")
                return None

            content_type = response.headers.get("content-type", "application/octet-stream")
            # An HTML body means we were bounced to a login/error page, not a file.
            if content_type.startswith("text/html"):
                logger.warning("Download returned HTML — session likely expired")
                return None

            filename = _filename_from_disposition(
                response.headers.get("content-disposition"), "document")
            return response.content, content_type, filename
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return None


async def validate_session(schulnetz_base_url: str, cookies: dict[str, str], session_id: str, transid: str, user_agent: str | None = None) -> bool:
    """Check if a PHP session is still valid."""
    html = await scrape_page(schulnetz_base_url, cookies, "21111", session_id, transid, user_agent=user_agent)
    if html is None:
        return False
    return "pageid" in html

async def fetch_scheduler_data(schulnetz_base_url: str, cookies: dict[str, str], session_id: str, transid: str, date: str | None = None, user_agent: str | None = None) -> str | None:
    """Fetch timetable/agenda data from the scheduler AJAX endpoint.

    The dhtmlxScheduler on pageid 22202 is driven by ``scheduler_processor.php``,
    but that endpoint needs the *fresh* transid the agenda page mints on load —
    replaying the stored session transid returns an empty ``<data/>``. So we GET
    the agenda page first, lift its transid, and pull a wide date window (the
    whole rest of the term) rather than a single week.
    """
    from datetime import datetime, timedelta

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    dt = datetime.strptime(date, "%Y-%m-%d")
    min_date = (dt - timedelta(days=35)).strftime("%Y-%m-%d")
    max_date = (dt + timedelta(days=120)).strftime("%Y-%m-%d")

    # Mint a fresh transid by loading the agenda page (pageid 22202).
    sched_transid = transid
    page_html = await scrape_page(schulnetz_base_url, cookies, "22202", session_id, transid, user_agent=user_agent)
    if page_html:
        m = re.search(r"transid=([a-f0-9]{4,})", page_html)
        if m:
            sched_transid = m.group(1)

    url = f"{schulnetz_base_url}/scheduler_processor.php"
    params = {
        "view": "week",
        "curr_date": date,
        "min_date": min_date,
        "max_date": max_date,
        "ansicht": "schueleransicht",
        "id": session_id,
        "transid": sched_transid,
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

async def save_semid(
    schulnetz_base_url: str,
    cookies: dict[str, str],
    session_id: str,
    transid: str,
    sem_id: str,
    user_agent: str | None = None,
) -> bool:
    """Set the session-active semester on the Noten page via its xajax call.

    The grades dropdown doesn't pass the semester as a URL param — its onchange
    fires ``xajax_save_semid(value, returnUrl)``, which POSTs to ``xajax_js.php``
    to store the chosen semester server-side in the session. A following GET of
    pageid 21311 then returns that semester's grades. The transid must be the
    *fresh* one the grades page minted on its last load (it rotates per request),
    so callers lift it from the page HTML before calling this.
    """
    import time

    url = f"{schulnetz_base_url}/xajax_js.php"
    params = {"pageid": "21311", "id": session_id, "transid": transid}
    return_url = f"index.php?pageid=21311&id={session_id}&transid={transid}&listindex_s="
    # xajaxargs[] is repeated once per positional argument (sem id, then return url).
    data = [
        ("xajax", "save_semid"),
        ("xajaxr", str(int(time.time() * 1000))),
        ("xajaxargs[]", sem_id),
        ("xajaxargs[]", return_url),
    ]

    headers = {
        **WEB_HEADERS,
        "Referer": f"{schulnetz_base_url}/",
        "Sec-Fetch-Site": "same-origin",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    if user_agent:
        headers["User-Agent"] = user_agent

    async with httpx.AsyncClient(headers=headers, cookies=cookies, follow_redirects=True, timeout=30.0) as client:
        try:
            response = await client.post(url, params=params, data=data)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to save semester {sem_id}: {e}")
            return False


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
