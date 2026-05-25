from dataclasses import dataclass
from typing import Any

from mediatorx import IQuery, IQueryHandler

from src.application.services.schulnetz_web_scrapers.agenda_scraper import scrape_agenda


@dataclass
class ScrapeAgendaQuery(IQuery[Any]):
    url: str


class ScrapeAgendaHandler(IQueryHandler[ScrapeAgendaQuery, Any]):
    async def handle(self, query: ScrapeAgendaQuery) -> Any:
        return await scrape_agenda(query.url)
