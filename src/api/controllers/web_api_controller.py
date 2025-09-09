from src.application.services.schulnetz_web_scrapers.unterricht_scraper import scrape_unterricht
from src.application.services.schulnetz_web_scrapers.agenda_scraper import scrape_agenda
from src.application.services.schulnetz_web_scrapers.listen_scraper import scrape_listen
from src.application.services.schulnetz_web_scrapers.ausweis_scraper import scrape_ausweis
from src.application.services.schulnetz_web_scrapers.noten_scraper import scrape_noten
from src.api.router_registry import SchulwareAPIRouter

router = SchulwareAPIRouter()

@router.get("unterricht")
async def get_unterricht(url: str):
    return await scrape_unterricht(url)

@router.get("agenda")
async def get_agenda(url: str):
    return await scrape_agenda(url)

@router.get("listen")
async def get_listen(url: str):
    return await scrape_listen(url)

@router.get("ausweis")
async def get_ausweis(url: str):
    return await scrape_ausweis(url)

@router.get("noten")
async def get_noten(url: str):
    return await scrape_noten(url)
