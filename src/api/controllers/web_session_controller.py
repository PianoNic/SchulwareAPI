from fastapi import APIRouter, Depends, Request
from mediatorx import Mediator

from src.api.controller import controller
from src.api.dependencies import get_mediator, get_schulnetz_base_url
from src.api.rate_limit import shared_limiter
from src.application.commands.capture_web_session_command import CaptureWebSessionCommand
from src.application.dtos.web_session_dtos import (
    WebScrapeRequestDto,
    WebScrapeResponseDto,
    WebSessionRequestDto,
    WebSessionResponseDto,
)
from src.application.queries.scrape_web_page_query import ScrapeWebPageQuery
from src.application.queries.validate_web_session_query import ValidateWebSessionQuery
from src.infrastructure.logging_config import get_logger

logger = get_logger("web_session_controller")

router = APIRouter(prefix="/api/websession", tags=["Web Session"])

@controller(router)
class WebSessionController:
    mediator: Mediator = Depends(get_mediator)

    @router.post("/capture", response_model=WebSessionResponseDto)
    @shared_limiter.limit("5/minute")
    async def capture_session(
        self,
        request: Request,
        body: WebSessionRequestDto,
        base_url: str = Depends(get_schulnetz_base_url),
    ):
        """Exchange an OAuth code for a Schulnetz PHP web session.
        Returns PHPSESSID cookie and session parameters (id, transid) needed for scraping.
        """
        return await self.mediator.send(
            CaptureWebSessionCommand(body.code, base_url, body.state, body.code_verifier)
        )

    @router.post("/scrape", response_model=WebScrapeResponseDto)
    @shared_limiter.limit("30/minute")
    async def scrape(
        self,
        request: Request,
        body: WebScrapeRequestDto,
        base_url: str = Depends(get_schulnetz_base_url),
    ):
        """Scrape and parse a Schulnetz page.

        Available pages: home, grades, absences, agenda, lessons, documents, student_id, schedule.
        Requires session_id (PHPSESSID), id, and transid from a previous /capture call.
        """
        return await self.mediator.send(ScrapeWebPageQuery(body, base_url=base_url))

    @router.post("/validate")
    @shared_limiter.limit("10/minute")
    async def validate(
        self,
        request: Request,
        body: WebScrapeRequestDto,
        base_url: str = Depends(get_schulnetz_base_url),
    ):
        """Check if a web session is still valid."""
        return await self.mediator.send(ValidateWebSessionQuery(body, base_url=base_url))
