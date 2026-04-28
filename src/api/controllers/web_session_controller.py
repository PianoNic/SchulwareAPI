from fastapi import Request, HTTPException
from src.api.router_registry import SchulwareAPIRouter, shared_limiter
from src.application.dtos.web_session_dtos import (
    WebSessionRequestDto,
    WebSessionResponseDto,
    WebScrapeRequestDto,
    WebScrapeResponseDto,
)
from src.application.services.web_session_service import (
    capture_web_session,
    scrape_page,
    validate_session,
)
from src.application.services.env_service import get_env_variable
from src.application.services import db_service
from src.infrastructure.logging_config import get_logger

router = SchulwareAPIRouter()
logger = get_logger("web_session_controller")


@router.post("capture", response_model=WebSessionResponseDto)
@shared_limiter.limit("5/minute")
async def capture_session(request: Request, body: WebSessionRequestDto):
    """
    Exchange an OAuth code for a Schulnetz PHP web session.

    Use the code from the mobile OAuth flow (or any Microsoft SSO flow)
    to capture a PHPSESSID cookie for web scraping. No browser needed.
    """
    base_url = get_env_variable("SCHULNETZ_WEB_BASE_URL")

    cookies, redirect_url = await capture_web_session(base_url, body.code, body.state)

    if cookies is None:
        return WebSessionResponseDto(
            success=False,
            message="Failed to capture web session. The code may be expired or invalid."
        )

    session_id = cookies.get("PHPSESSID")

    logger.info(f"Web session captured. PHPSESSID: {session_id is not None}, cookies: {len(cookies)}")

    return WebSessionResponseDto(
        success=True,
        session_id=session_id,
        cookies=cookies,
        message="Web session captured successfully"
    )


@router.post("scrape", response_model=WebScrapeResponseDto)
@shared_limiter.limit("30/minute")
async def scrape(request: Request, body: WebScrapeRequestDto):
    """
    Scrape a Schulnetz page using stored session cookies.

    Requires a valid PHPSESSID from a previous /capture call.
    Pass the session cookies in the Authorization header as Bearer token,
    or provide them in the request body.
    """
    # For now, get cookies from the user's stored session
    # TODO: integrate with user session storage
    return WebScrapeResponseDto(
        success=False,
        message="Scrape endpoint ready. Integrate with session storage to use."
    )


@router.post("validate")
@shared_limiter.limit("10/minute")
async def validate(request: Request, body: WebSessionRequestDto):
    """
    Validate if a web session is still active.
    """
    base_url = get_env_variable("SCHULNETZ_WEB_BASE_URL")

    # First capture the session
    cookies, _ = await capture_web_session(base_url, body.code, body.state)

    if cookies is None:
        return {"valid": False, "message": "Could not establish session"}

    is_valid = await validate_session(base_url, cookies)

    return {"valid": is_valid, "message": "Session is active" if is_valid else "Session expired"}
