from fastapi import Depends, Request
from mediatorx import Mediator

from src.api.dependencies import get_mediator
from src.api.router_registry import SchulwareAPIRouter, shared_limiter
from src.application.commands.capture_web_session_command import CaptureWebSessionCommand
from src.application.dtos.web_session_dtos import (
    WebSessionRequestDto,
    WebSessionResponseDto,
    WebScrapeRequestDto,
    WebScrapeResponseDto,
)
from src.application.queries.scrape_web_page_query import ScrapeWebPageQuery
from src.application.queries.validate_web_session_query import ValidateWebSessionQuery

router = SchulwareAPIRouter()


@router.post("capture", response_model=WebSessionResponseDto)
@shared_limiter.limit("5/minute")
async def capture_session(
    request: Request,
    body: WebSessionRequestDto,
    mediator: Mediator = Depends(get_mediator),
):
    """
    Exchange an OAuth code for a Schulnetz PHP web session.
    Returns PHPSESSID cookie and session parameters (id, transid) needed for scraping.
    """
    return await mediator.send(CaptureWebSessionCommand(body.code, body.state))


@router.post("scrape", response_model=WebScrapeResponseDto)
@shared_limiter.limit("30/minute")
async def scrape(
    request: Request,
    body: WebScrapeRequestDto,
    mediator: Mediator = Depends(get_mediator),
):
    """
    Scrape and parse a Schulnetz page.

    Available pages: home, grades, absences, agenda, lessons, documents, student_id, schedule

    Requires session_id (PHPSESSID), id, and transid from a previous /capture call.
    """
    return await mediator.send(ScrapeWebPageQuery(body))


@router.post("validate")
@shared_limiter.limit("10/minute")
async def validate(
    request: Request,
    body: WebScrapeRequestDto,
    mediator: Mediator = Depends(get_mediator),
):
    """Check if a web session is still valid."""
    return await mediator.send(ValidateWebSessionQuery(body))
