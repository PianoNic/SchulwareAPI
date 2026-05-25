from fastapi import APIRouter, Depends
from mediatorx import Mediator

from src.api.controller import controller
from src.api.dependencies import get_mediator
from src.application.queries.scrape_agenda_query import ScrapeAgendaQuery
from src.application.queries.scrape_ausweis_query import ScrapeAusweisQuery
from src.application.queries.scrape_listen_query import ScrapeListenQuery
from src.application.queries.scrape_noten_query import ScrapeNotenQuery
from src.application.queries.scrape_unterricht_query import ScrapeUnterrichtQuery

router = APIRouter(prefix="/api/web", tags=["Web API"])

@controller(router)
class WebApiController:
    mediator: Mediator = Depends(get_mediator)

    @router.get("/unterricht")
    async def get_unterricht(self, url: str):
        return await self.mediator.send(ScrapeUnterrichtQuery(url))

    @router.get("/agenda")
    async def get_agenda(self, url: str):
        return await self.mediator.send(ScrapeAgendaQuery(url))

    @router.get("/listen")
    async def get_listen(self, url: str):
        return await self.mediator.send(ScrapeListenQuery(url))

    @router.get("/ausweis")
    async def get_ausweis(self, url: str):
        return await self.mediator.send(ScrapeAusweisQuery(url))

    @router.get("/noten")
    async def get_noten(self, url: str):
        return await self.mediator.send(ScrapeNotenQuery(url))
