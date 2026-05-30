from dataclasses import dataclass

from mediatorx import IQuery, IQueryHandler

from src.application.dtos.web_session_dtos import WebScrapeRequestDto, WebScrapeResponseDto
from src.application.services.schulnetz_web_scrapers.absenz_scraper import scrape_absences
from src.application.services.schulnetz_web_scrapers.agenda_scraper import scrape_agenda
from src.application.services.schulnetz_web_scrapers.ausweis_scraper import scrape_ausweis
from src.application.services.schulnetz_web_scrapers.home_scraper import scrape_home
from src.application.services.schulnetz_web_scrapers.listen_scraper import scrape_listen
from src.application.services.schulnetz_web_scrapers.noten_scraper import scrape_noten
from src.application.services.schulnetz_web_scrapers.schedule_scraper import parse_scheduler_xml
from src.application.services.schulnetz_web_scrapers.unterricht_scraper import scrape_unterricht
from src.application.services.web_session_service import fetch_scheduler_data, scrape_page
from src.infrastructure.logging_config import get_logger

logger = get_logger("scrape_web_page_query")

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
