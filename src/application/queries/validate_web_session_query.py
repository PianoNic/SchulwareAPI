from dataclasses import dataclass

from mediatorx import IQuery, IQueryHandler

from src.application.dtos.web_session_dtos import WebScrapeRequestDto, WebValidateResponseDto
from src.application.services.web_session_service import validate_session


@dataclass
class ValidateWebSessionQuery(IQuery[WebValidateResponseDto]):
    body: WebScrapeRequestDto
    base_url: str = ""


class ValidateWebSessionHandler(IQueryHandler[ValidateWebSessionQuery, WebValidateResponseDto]):
    async def handle(self, query: ValidateWebSessionQuery) -> WebValidateResponseDto:
        body = query.body
        base_url = query.base_url.rstrip("/")
        cookies = {"PHPSESSID": body.session_id}

        is_valid, refreshed_id, refreshed_transid = await validate_session(
            base_url,
            cookies,
            body.id,
            body.transid,
            user_agent=body.user_agent,
            additional_cookies=body.additional_cookies,
        )
        return WebValidateResponseDto(
            valid=is_valid,
            message="Session is active" if is_valid else "Session expired",
            refreshed_id=refreshed_id,
            refreshed_transid=refreshed_transid,
        )
