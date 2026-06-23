from fastapi import APIRouter, Depends, Request, Response
from mediatorx import Mediator

from src.api.controller import controller
from src.api.dependencies import get_mediator, get_schulnetz_base_url
from src.api.rate_limit import shared_limiter
from src.application.dtos.web_session_dtos import (
    WebDownloadRequestDto,
    WebScrapeRequestDto,
    WebScrapeResponseDto,
)
from src.application.queries.scrape_web_page_query import ScrapeWebPageQuery
from src.application.queries.validate_web_session_query import ValidateWebSessionQuery
from src.application.services.web_session_service import download_file
from src.infrastructure.logging_config import get_logger

logger = get_logger("web_session_controller")

router = APIRouter(prefix="/api/websession", tags=["Web Session"])

@controller(router)
class WebSessionController:
    mediator: Mediator = Depends(get_mediator)

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
        Requires session_id (PHPSESSID), id, and transid from a previous /api/authenticate/login call.
        """
        return await self.mediator.send(ScrapeWebPageQuery(body, base_url=base_url))

    @router.post("/download")
    @shared_limiter.limit("30/minute")
    async def download(
        self,
        request: Request,
        body: WebDownloadRequestDto,
        base_url: str = Depends(get_schulnetz_base_url),
    ):
        """Download a filestore document's raw bytes via the stored web session.

        Pass the relative `download_url` from a documents scrape plus the
        PHPSESSID (`session_id`) and the UA the session was created with.
        Returns the file inline (502 if the session expired).
        """
        result = await download_file(
            base_url, {"PHPSESSID": body.session_id}, body.download_url, user_agent=body.user_agent)
        if result is None:
            return Response(status_code=502, content="Download failed or session expired")
        content, content_type, filename = result
        return Response(
            content=content,
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

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
