from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from src.application.models.event import Event  # Just for demo, replace with your own model
from src.application.services.schulnetz_web_scrapers.unterricht_scraper import scrape_unterricht
from src.application.services.schulnetz_web_scrapers.agenda_scraper import scrape_agenda
from src.application.services.schulnetz_web_scrapers.listen_scraper import scrape_listen
from src.application.services.schulnetz_web_scrapers.ausweis_scraper import scrape_ausweis
from src.application.services.schulnetz_web_scrapers.noten_scraper import scrape_noten

router = APIRouter()
router_tag = ["Web API"]

@router.get("/api/web/unterricht", tags=router_tag)
async def get_unterricht(url: str):
    """Scrape Unterricht section"""
    return await scrape_unterricht(url)

@router.get("/api/web/agenda", tags=router_tag)
async def get_agenda(url: str):
    """Scrape Agenda section"""
    return await scrape_agenda(url)

@router.get("/api/web/listen", tags=router_tag)
async def get_listen(url: str):
    """Scrape Listen & Dokumente section"""
    return await scrape_listen(url)

@router.get("/api/web/ausweis", tags=router_tag)
async def get_ausweis(url: str):
    """Scrape Ausweis section"""
    return await scrape_ausweis(url)

@router.get("/api/web/noten", tags=router_tag)
async def get_noten(url: str):
    """Scrape Noten section"""
    return await scrape_noten(url)
