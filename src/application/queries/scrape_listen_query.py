from dataclasses import dataclass
from typing import Any

from mediatorx import IQuery, IQueryHandler

from src.application.services.schulnetz_web_scrapers.listen_scraper import scrape_listen


@dataclass
class ScrapeListenQuery(IQuery[Any]):
    url: str


class ScrapeListenHandler(IQueryHandler[ScrapeListenQuery, Any]):
    async def handle(self, query: ScrapeListenQuery) -> Any:
        return await scrape_listen(query.url)
