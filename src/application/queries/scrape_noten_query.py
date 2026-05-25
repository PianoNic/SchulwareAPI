from dataclasses import dataclass
from typing import Any

from mediatorx import IQuery, IQueryHandler

from src.application.services.schulnetz_web_scrapers.noten_scraper import scrape_noten

@dataclass
class ScrapeNotenQuery(IQuery[Any]):
    url: str

class ScrapeNotenHandler(IQueryHandler[ScrapeNotenQuery, Any]):
    async def handle(self, query: ScrapeNotenQuery) -> Any:
        return await scrape_noten(query.url)
