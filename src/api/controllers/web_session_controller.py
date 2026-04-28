from typing import Optional
from fastapi import Request, Query
from src.api.router_registry import SchulwareAPIRouter, shared_limiter
from src.application.dtos.web_session_dtos import (
    WebSessionRequestDto,
    WebSessionResponseDto,
    WebScrapeRequestDto,
    WebScrapeResponseDto,
)
from src.application.services.web_session_service import (
    capture_web_session,
    scrape_page,
    validate_session,
    fetch_scheduler_data,
)
from src.application.services.schulnetz_web_scrapers.home_scraper import scrape_home
from src.application.services.schulnetz_web_scrapers.noten_scraper import scrape_noten
from src.application.services.schulnetz_web_scrapers.absenz_scraper import scrape_absences
from src.application.services.schulnetz_web_scrapers.agenda_scraper import scrape_agenda
from src.application.services.schulnetz_web_scrapers.unterricht_scraper import scrape_unterricht
from src.application.services.schulnetz_web_scrapers.listen_scraper import scrape_listen
from src.application.services.schulnetz_web_scrapers.ausweis_scraper import scrape_ausweis
from src.application.services.schulnetz_web_scrapers.schedule_scraper import parse_scheduler_xml
from src.application.services.env_service import get_env_variable
from src.infrastructure.logging_config import get_logger

router = SchulwareAPIRouter()
logger = get_logger("web_session_controller")

SCRAPERS = {
    "home": ("1", scrape_home),
    "grades": ("21311", scrape_noten),
    "absences": ("21111", scrape_absences),
    "agenda": ("21200", scrape_agenda),
    "lessons": ("21355", scrape_unterricht),
    "documents": ("10053", scrape_listen),
    "student_id": ("50505", scrape_ausweis),
}


@router.post("capture", response_model=WebSessionResponseDto)
@shared_limiter.limit("5/minute")
async def capture_session(request: Request, body: WebSessionRequestDto):
    """
    Exchange an OAuth code for a Schulnetz PHP web session.
    Returns PHPSESSID cookie and session parameters (id, transid) needed for scraping.
    """
    base_url = get_env_variable("SCHULNETZ_WEB_BASE_URL")

    cookies, session_info = await capture_web_session(base_url, body.code, body.state)

    if cookies is None:
        return WebSessionResponseDto(
            success=False,
            message="Failed to capture web session. The code may be expired or invalid."
        )

    return WebSessionResponseDto(
        success=True,
        session_id=cookies.get("PHPSESSID"),
        cookies=cookies,
        session_info=session_info,
        message="Web session captured successfully"
    )


@router.post("scrape", response_model=WebScrapeResponseDto)
@shared_limiter.limit("30/minute")
async def scrape(request: Request, body: WebScrapeRequestDto):
    """
    Scrape and parse a Schulnetz page.

    Available pages: home, grades, absences, agenda, lessons, documents, student_id, schedule

    Requires session_id (PHPSESSID), id, and transid from a previous /capture call.
    """
    if body.page == "schedule":
        return await _scrape_schedule(body)

    if body.page not in SCRAPERS:
        available = list(SCRAPERS.keys()) + ["schedule"]
        return WebScrapeResponseDto(
            success=False,
            message=f"Unknown page '{body.page}'. Available: {', '.join(available)}"
        )

    pageid, parser = SCRAPERS[body.page]
    base_url = get_env_variable("SCHULNETZ_WEB_BASE_URL")
    cookies = {"PHPSESSID": body.session_id}

    html = await scrape_page(base_url, cookies, pageid, body.id, body.transid)

    if html is None:
        return WebScrapeResponseDto(
            success=False,
            message="Session expired or page not accessible. Re-authenticate with /capture."
        )

    try:
        data = parser(html)
        return WebScrapeResponseDto(success=True, data=data)
    except Exception as e:
        logger.error(f"Scraper error for {body.page}: {e}")
        return WebScrapeResponseDto(success=False, message=f"Parsing error: {str(e)}")


async def _scrape_schedule(body: WebScrapeRequestDto) -> WebScrapeResponseDto:
    base_url = get_env_variable("SCHULNETZ_WEB_BASE_URL")
    cookies = {"PHPSESSID": body.session_id}

    xml = await fetch_scheduler_data(base_url, cookies, body.id, body.transid)

    if xml is None:
        return WebScrapeResponseDto(
            success=False,
            message="Session expired or schedule not accessible."
        )

    try:
        events = parse_scheduler_xml(xml)
        return WebScrapeResponseDto(success=True, data=events)
    except Exception as e:
        logger.error(f"Schedule parser error: {e}")
        return WebScrapeResponseDto(success=False, message=f"Parsing error: {str(e)}")


@router.post("validate")
@shared_limiter.limit("10/minute")
async def validate(request: Request, body: WebScrapeRequestDto):
    """Check if a web session is still valid."""
    base_url = get_env_variable("SCHULNETZ_WEB_BASE_URL")
    cookies = {"PHPSESSID": body.session_id}

    is_valid = await validate_session(base_url, cookies, body.id, body.transid)
    return {"valid": is_valid, "message": "Session is active" if is_valid else "Session expired"}
