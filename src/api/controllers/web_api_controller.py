from fastapi import APIRouter
from src.application.dtos.web.schulnetz_data_dto import SchulnetzDataDto
from src.application.services.schulnetz_web_service import get_schulnetz_web_html_authenticated
from src.application.services.schulnetz_web_scrapers.home_scraper import scrape_home
from src.application.services.schulnetz_web_scrapers.unterricht_scraper import scrape_unterricht
from src.application.services.schulnetz_web_scrapers.agenda_scraper import scrape_agenda
from src.application.services.schulnetz_web_scrapers.listen_scraper import scrape_listen
from src.application.services.schulnetz_web_scrapers.ausweis_scraper import scrape_ausweis
from src.application.services.schulnetz_web_scrapers.noten_scraper import scrape_noten

router = APIRouter()
router_tag = ["Web API"]

@router.get("/api/web/home", tags=router_tag, response_model=SchulnetzDataDto)
async def get_unterricht():
    html = await get_schulnetz_web_html_authenticated(pageid="1", id="e4d91463a45155f3", transid="d316ad", php_sessid="p04gi6r3fi8gr7spq6qgeqnu3t")
    return await scrape_home(html)

@router.get("/api/web/unterricht", tags=router_tag)
async def get_unterricht(url: str):
    return await scrape_unterricht(url)

@router.get("/api/web/agenda", tags=router_tag)
async def get_agenda(url: str):
    return await scrape_agenda(url)

@router.get("/api/web/listen", tags=router_tag)
async def get_listen(url: str):
    return await scrape_listen(url)

@router.get("/api/web/ausweis", tags=router_tag)
async def get_ausweis(url: str):
    return await scrape_ausweis(url)

@router.get("/api/web/noten", tags=router_tag)
async def get_noten(url: str):
    return await scrape_noten(url)
