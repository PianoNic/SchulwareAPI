import re
from dataclasses import dataclass
from datetime import date

import httpx

from mediatorx import IQuery, IQueryHandler

from src.application.dtos.web_session_dtos import WebScrapeRequestDto, WebScrapeResponseDto
from src.application.services.schulnetz_web_scrapers.absenz_scraper import scrape_absences
from src.application.services.schulnetz_web_scrapers.agenda_scraper import scrape_agenda
from src.application.services.schulnetz_web_scrapers.ausweis_scraper import scrape_ausweis
from src.application.services.schulnetz_web_scrapers.home_scraper import scrape_home
from src.application.services.schulnetz_web_scrapers.listen_scraper import scrape_listen
from src.application.dtos.web.scrape_dtos import GradesPageDto
from src.application.services.schulnetz_web_scrapers.noten_scraper import parse_semester_options, scrape_noten
from src.application.services.schulnetz_web_scrapers.schedule_scraper import parse_scheduler_xml
from src.application.services.schulnetz_web_scrapers.unterricht_scraper import scrape_unterricht
from src.application.services.web_session_service import WEB_HEADERS, fetch_scheduler_data, save_semid, scrape_page
from src.infrastructure.logging_config import get_logger

logger = get_logger("scrape_web_page_query")

# Stop walking back through semesters after this many consecutive empty ones —
# the dropdown lists every term the school ever had, but a student only has data
# in a handful of recent ones.
_MAX_EMPTY_SEMESTERS = 2
_TRANSID_RE = re.compile(r"transid=([a-f0-9]{4,})")
_SEMESTER_RE = re.compile(r"^([12])\.\s*(\d{2})/\d{2}$")


def semester_key(label: str) -> tuple[int, int] | None:
    """Orders a semester label like ``"1. 25/26"`` as ``(2025, 1)``; None when it isn't one."""
    m = _SEMESTER_RE.match(label.strip())
    return (2000 + int(m.group(2)), int(m.group(1))) if m else None


def current_semester_key(today: date) -> tuple[int, int]:
    """The Swiss school year runs Aug-Jul: Aug-Jan is the 1st semester, Feb-Jul the 2nd."""
    if today.month >= 8:
        return (today.year, 1)
    return (today.year - 1, 1) if today.month == 1 else (today.year - 1, 2)


async def _scrape_all_semester_grades(base_url: str, cookies: dict[str, str], session_id: str, transid: str, user_agent: str | None, semesters: list[str] | None = None, today: date | None = None) -> GradesPageDto | None:
    """Scrape grades across semesters and merge their courses, each tagged with its semester.

    The Noten page shows one semester at a time, switched server-side via ``save_semid``.
    The dropdown is newest-first and starts with years of empty future terms, so the walk
    skips everything after the current semester. With ``semesters`` only those labels are
    fetched; otherwise it walks back until two empty terms in a row end the history. One
    connection is reused for the whole walk, and the session's semester is restored after.
    """
    headers = {**WEB_HEADERS, "Referer": f"{base_url}/", "Sec-Fetch-Site": "same-origin"}
    if user_agent:
        headers["User-Agent"] = user_agent
    async with httpx.AsyncClient(headers=headers, cookies=cookies, follow_redirects=True, timeout=30.0) as client:
        html = await scrape_page(base_url, cookies, "21311", session_id, transid, user_agent=user_agent, client=client)
        if html is None:
            logger.warning("grades: initial Noten page load returned None (web session expired / redirect)")
            return None

        options = parse_semester_options(html)
        student = scrape_noten(html).student
        if not options:
            page0 = scrape_noten(html)
            logger.info("grades: no semester switcher; %d courses on the visible page", len(page0.courses))
            return page0

        current = current_semester_key(today or date.today())
        wanted = {label.strip() for label in semesters} if semesters else None
        candidates = [
            (sem_id, label) for sem_id, label, _ in options
            if (key := semester_key(label)) is None or key <= current
            if wanted is None or label.strip() in wanted
        ]
        original = next((sid for sid, _, sel in options if sel), options[0][0])
        fresh = (m.group(1) if (m := _TRANSID_RE.search(html)) else None) or transid

        merged: list = []
        empty = 0
        seen_data = False
        for sem_id, label in candidates:
            if not await save_semid(base_url, cookies, session_id, fresh, sem_id, user_agent=user_agent, client=client):
                break
            page_html = await scrape_page(base_url, cookies, "21311", session_id, transid, user_agent=user_agent, client=client)
            if page_html is None:
                break
            if m := _TRANSID_RE.search(page_html):
                fresh = m.group(1)
            page = scrape_noten(page_html)
            logger.info("grades: sem %s (%s) -> %d courses", label, sem_id, len(page.courses))
            if page.courses:
                merged.extend(course.model_copy(update={"semester": label}) for course in page.courses)
                empty = 0
                seen_data = True
            elif seen_data and wanted is None:
                empty += 1
                if empty >= _MAX_EMPTY_SEMESTERS:
                    break

        await save_semid(base_url, cookies, session_id, fresh, original, user_agent=user_agent, client=client)
    logger.info("grades: merged %d courses from %d of %d semesters", len(merged), len(candidates), len(options))
    return GradesPageDto(student=student, courses=merged)

SCRAPERS = {
    "home": ("1", scrape_home),
    "grades": ("21311", scrape_noten),
    "absences": ("21111", scrape_absences),
    "agenda": ("21200", scrape_agenda),
    "lessons": ("21355", scrape_unterricht),
    "documents": ("10053", scrape_listen),
    "student_id": ("50505", scrape_ausweis),
}


@dataclass
class ScrapeWebPageQuery(IQuery[WebScrapeResponseDto]):
    body: WebScrapeRequestDto
    base_url: str = ""


class ScrapeWebPageHandler(IQueryHandler[ScrapeWebPageQuery, WebScrapeResponseDto]):
    async def handle(self, query: ScrapeWebPageQuery) -> WebScrapeResponseDto:
        body = query.body
        base_url = query.base_url.rstrip("/")
        cookies = {"PHPSESSID": body.session_id}

        if body.page == "grades":
            grades = await _scrape_all_semester_grades(
                base_url, cookies, body.id, body.transid, body.user_agent, body.semesters)
            if grades is None:
                return WebScrapeResponseDto(
                    success=False,
                    message="Session expired or page not accessible. Re-authenticate with /api/authenticate/login.",
                )
            return WebScrapeResponseDto(success=True, grades=grades)

        if body.page == "schedule":
            xml = await fetch_scheduler_data(base_url, cookies, body.id, body.transid, user_agent=body.user_agent)
            if xml is None:
                return WebScrapeResponseDto(success=False, message="Session expired or schedule not accessible.")
            try:
                return WebScrapeResponseDto(success=True, schedule=parse_scheduler_xml(xml))
            except Exception as e:
                logger.error(f"Schedule parser error: {e}")
                return WebScrapeResponseDto(success=False, message=f"Parsing error: {str(e)}")

        if body.page not in SCRAPERS:
            available = list(SCRAPERS.keys()) + ["schedule"]
            return WebScrapeResponseDto(
                success=False,
                message=f"Unknown page '{body.page}'. Available: {', '.join(available)}",
            )

        pageid, parser = SCRAPERS[body.page]
        html = await scrape_page(base_url, cookies, pageid, body.id, body.transid, user_agent=body.user_agent)
        if html is None:
            return WebScrapeResponseDto(
                success=False,
                message="Session expired or page not accessible. Re-authenticate with /capture.",
            )

        try:
            # Each scraper returns its page's typed model; place it in the matching field.
            return WebScrapeResponseDto(success=True, **{body.page: parser(html)})
        except Exception as e:
            logger.error(f"Scraper error for {body.page}: {e}")
            return WebScrapeResponseDto(success=False, message=f"Parsing error: {str(e)}")
