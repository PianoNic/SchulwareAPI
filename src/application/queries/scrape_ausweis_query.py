from dataclasses import dataclass
from typing import Any

from mediatorx import IQuery, IQueryHandler

from src.application.services.schulnetz_web_scrapers.ausweis_scraper import scrape_ausweis


@dataclass
class ScrapeAusweisQuery(IQuery[Any]):
    url: str


class ScrapeAusweisHandler(IQueryHandler[ScrapeAusweisQuery, Any]):
    async def handle(self, query: ScrapeAusweisQuery) -> Any:
        return await scrape_ausweis(query.url)
