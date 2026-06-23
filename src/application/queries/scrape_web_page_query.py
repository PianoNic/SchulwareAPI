import re
from dataclasses import dataclass

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
from src.application.services.web_session_service import fetch_scheduler_data, save_semid, scrape_page
from src.infrastructure.logging_config import get_logger

logger = get_logger("scrape_web_page_query")

# Stop walking back through semesters after this many consecutive empty ones —
# the dropdown lists every term the school ever had, but a student only has data
# in a handful of recent ones.
_MAX_EMPTY_SEMESTERS = 2
_TRANSID_RE = re.compile(r"transid=([a-f0-9]{4,})")


async def _scrape_all_semester_grades(
    base_url: str, cookies: dict[str, str], session_id: str, transid: str, user_agent: str | None
) -> GradesPageDto | None:
    """Scrape grades across recent semesters and merge their courses.

    The Noten page shows one semester at a time. We read the current page, then
    walk the semester dropdown newest-first, setting each via ``save_semid`` and
    re-scraping, until we hit two empty semesters in a row. The session's active
    semester is restored at the end so we don't disturb other scrapers.
    """
    html = await scrape_page(base_url, cookies, "21311", session_id, transid, user_agent=user_agent)
    if html is None:
        logger.warning("grades: initial Noten page load returned None (web session expired / redirect)")
        return None

    options = parse_semester_options(html)
    student = scrape_noten(html).student
    logger.info("grades: %d semester options: %s", len(options),
                [f"{lbl}{'*' if sel else ''}" for _, lbl, sel in options])
    if not options:
        # No switcher — just the single visible semester.
        page0 = scrape_noten(html)
        logger.info("grades: no semester switcher; %d courses on the visible page", len(page0.courses))
        return page0

    original = next((sid for sid, _, sel in options if sel), options[0][0])
    fresh = (m.group(1) if (m := _TRANSID_RE.search(html)) else None) or transid

    # The dropdown is newest-first: a few (always-empty) *future* placeholder
    # terms, then the current term, then history. We must NOT start at the
    # session-selected semester — a session captured in an earlier term stays
    # pinned there, so the current term (with the student's newest grades) can sit
    # *above* the selected one and would be missed. Instead walk the whole list:
    # skip leading empty placeholders without counting them, and once we've seen
    # real data, stop after two empty terms in a row (the end of history).
    merged: list = []
    empty = 0
    seen_data = False
    for sem_id, label, _ in options:
        if not await save_semid(base_url, cookies, session_id, fresh, sem_id, user_agent=user_agent):
            break
        page_html = await scrape_page(base_url, cookies, "21311", session_id, transid, user_agent=user_agent)
        if page_html is None:
            break
        if m := _TRANSID_RE.search(page_html):
            fresh = m.group(1)
        page = scrape_noten(page_html)
        logger.info("grades: sem %s (%s) -> %d courses", label, sem_id, len(page.courses))
        if page.courses:
            merged.extend(page.courses)
            empty = 0
            seen_data = True
        elif seen_data:
            empty += 1
            if empty >= _MAX_EMPTY_SEMESTERS:
                break
        # else: leading future placeholder above the current term — keep looking.

    # Put the session back on the semester it started on.
    await save_semid(base_url, cookies, session_id, fresh, original, user_agent=user_agent)
    logger.info("grades: merged %d courses across %d semesters", len(merged), len(options))
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
                base_url, cookies, body.id, body.transid, body.user_agent)
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
