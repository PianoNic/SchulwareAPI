from dataclasses import dataclass
from typing import Any

from mediatorx import IQuery, IQueryHandler

from src.application.services.schulnetz_web_scrapers.unterricht_scraper import scrape_unterricht


@dataclass
class ScrapeUnterrichtQuery(IQuery[Any]):
    url: str


class ScrapeUnterrichtHandler(IQueryHandler[ScrapeUnterrichtQuery, Any]):
    async def handle(self, query: ScrapeUnterrichtQuery) -> Any:
        return await scrape_unterricht(query.url)
