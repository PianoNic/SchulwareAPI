from fastapi import Depends
from mediatorx import Mediator

from src.api.dependencies import get_mediator
from src.api.router_registry import SchulwareAPIRouter
from src.application.queries.scrape_unterricht_query import ScrapeUnterrichtQuery
from src.application.queries.scrape_agenda_query import ScrapeAgendaQuery
from src.application.queries.scrape_listen_query import ScrapeListenQuery
from src.application.queries.scrape_ausweis_query import ScrapeAusweisQuery
from src.application.queries.scrape_noten_query import ScrapeNotenQuery

router = SchulwareAPIRouter()

@router.get("unterricht")
async def get_unterricht(url: str, mediator: Mediator = Depends(get_mediator)):
    return await mediator.send(ScrapeUnterrichtQuery(url))

@router.get("agenda")
async def get_agenda(url: str, mediator: Mediator = Depends(get_mediator)):
    return await mediator.send(ScrapeAgendaQuery(url))

@router.get("listen")
async def get_listen(url: str, mediator: Mediator = Depends(get_mediator)):
    return await mediator.send(ScrapeListenQuery(url))

@router.get("ausweis")
async def get_ausweis(url: str, mediator: Mediator = Depends(get_mediator)):
    return await mediator.send(ScrapeAusweisQuery(url))

@router.get("noten")
async def get_noten(url: str, mediator: Mediator = Depends(get_mediator)):
    return await mediator.send(ScrapeNotenQuery(url))
