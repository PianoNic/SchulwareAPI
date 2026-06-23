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

async def discover_web_oauth(schulnetz_base_url: str) -> tuple[str, dict[str, str]]:
    """Start the OAuth flow from the school root, like a browser.

    GET `/` (unauthenticated), follow the redirect chain to the Microsoft
    authorize URL, and return it together with the anonymous PHPSESSID the school
    set. The root flow uses redirect_uri=`/` (no PKCE), so the eventual callback
    lands on `/` and renders the full dashboard (with id/transid) — unlike
    authorize.php, whose callback returns to itself on a bare page.
    """
    async with httpx.AsyncClient(headers=WEB_HEADERS, follow_redirects=True, timeout=30.0) as client:
        r = await client.get(f"{schulnetz_base_url}/")
        anon: dict[str, str] = {}
        for resp in r.history + [r]:
            anon.update(dict(resp.cookies))
        logger.info(f"Discovered web authorize URL via root; anon cookies: {list(anon.keys())}")
        return str(r.url), anon


async def capture_web_session(
    schulnetz_base_url: str,
    callback_url: str,
    code_verifier: str | None = None,
    seed_cookies: dict[str, str] | None = None,
) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    """
    Deliver the Microsoft → Schulnetz OAuth callback to establish a PHP web session.

    `callback_url` is the raw redirect Microsoft issues back to the provider, e.g.
    ``https://schulnetz.bbbaden.ch/?code=..&state=..&session_state=..``. Delivering
    it WHOLE — session_state included — is what makes Schulnetz complete the login
    and render the full dashboard (whose links carry id/transid). A reconstructed
    code-only exchange instead lands on a bare loginto.php page with neither.
    `code_verifier` is appended as a fallback for PKCE-enforced instances if the
    bare callback doesn't establish a session.

    Returns:
        Tuple of (cookies_dict, session_info) or (None, None) if failed.
        session_info contains: id, transid, navigation_urls from the dashboard.
    """
    def _collect(resp) -> dict[str, str]:
        c: dict[str, str] = {}
        for r in resp.history + [resp]:
            c.update(dict(r.cookies))
        return c

    logger.info("Delivering web OAuth callback to Schulnetz")

    async with httpx.AsyncClient(headers=WEB_HEADERS, follow_redirects=True, timeout=30.0, cookies=seed_cookies or {}) as client:
        try:
            response = await client.get(callback_url)
            cookies = _collect(response)
            session_info = _extract_session_info(str(response.url), response.text)

            # PKCE-enforced instances may need the verifier on the callback to
            # complete the exchange — retry with it appended if the bare callback
            # didn't yield a full session (id + transid).
            full = (
                "PHPSESSID" in cookies and session_info
                and session_info.get("id") and session_info.get("transid")
            )
            if code_verifier and not full:
                sep = "&" if "?" in callback_url else "?"
                response = await client.get(f"{callback_url}{sep}code_verifier={code_verifier}")
                cookies = _collect(response) or cookies
                follow = _extract_session_info(str(response.url), response.text)
                if follow:
                    session_info = {**(session_info or {}), **follow}

            logger.info(f"Final status: {response.status_code}, URL: {response.url}")
            logger.info(f"Cookies captured: {list(cookies.keys())}")

            if "PHPSESSID" not in cookies:
                logger.warning("No PHPSESSID captured — login may have failed")
                return None, None

            logger.info(f"Session captured. PHPSESSID: {cookies['PHPSESSID'][:20]}...")
            if session_info:
                logger.info(f"Session id: {session_info.get('id')}, transid: {session_info.get('transid')}, pages: {len(session_info.get('navigation_urls', {}))}")

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

    # Dashboard links (index.php?pageid=..&id=..&transid=..) carry id/transid even
    # when the landing URL doesn't — fall back to the page body for both.
    if not info.get("id"):
        m = re.search(r'[?&]id=([a-f0-9]+)', html)
        if m:
            info["id"] = m.group(1)
    if not info.get("transid"):
        m = re.search(r'[?&]transid=([a-f0-9]+)', html)
        if m:
            info["transid"] = m.group(1)

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
    # Schulnetz binds the PHPSESSID to the UA that created it. The refresh runner
    # mints the session in a browser using the account UA, so the scrape must
    # replay that same UA — otherwise the session is rejected.
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
    # Schulnetz binds the PHPSESSID to the UA that created it. The refresh runner
    # mints the session in a browser using the account UA, so the scrape must
    # replay that same UA — otherwise the session is rejected.
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
    # Schulnetz binds the PHPSESSID to the UA that created it. The refresh runner
    # mints the session in a browser using the account UA, so the scrape must
    # replay that same UA — otherwise the session is rejected.
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
    from urllib.parse import urlencode

    url = f"{schulnetz_base_url}/xajax_js.php"
    params = {"pageid": "21311", "id": session_id, "transid": transid}
    return_url = f"index.php?pageid=21311&id={session_id}&transid={transid}&listindex_s="
    # xajaxargs[] is repeated once per positional argument (sem id, then return url).
    # Encode the body ourselves and send it as raw content: httpx 0.28 wraps
    # `data=` form payloads in a SyncByteStream that AsyncClient refuses to send.
    body = urlencode([
        ("xajax", "save_semid"),
        ("xajaxr", str(int(time.time() * 1000))),
        ("xajaxargs[]", sem_id),
        ("xajaxargs[]", return_url),
    ])

    headers = {
        **WEB_HEADERS,
        "Referer": f"{schulnetz_base_url}/",
        "Sec-Fetch-Site": "same-origin",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    # Schulnetz binds the PHPSESSID to the UA that created it. The refresh runner
    # mints the session in a browser using the account UA, so the scrape must
    # replay that same UA — otherwise the session is rejected.
    if user_agent:
        headers["User-Agent"] = user_agent

    async with httpx.AsyncClient(headers=headers, cookies=cookies, follow_redirects=True, timeout=30.0) as client:
        try:
            response = await client.post(url, params=params, content=body)
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
