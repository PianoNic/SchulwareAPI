from dataclasses import dataclass
from typing import Any

from mediatorx import IQuery, IQueryHandler

from src.application.dtos.web_session_dtos import WebScrapeRequestDto
from src.application.services.env_service import get_env_variable
from src.application.services.web_session_service import validate_session


@dataclass
class ValidateWebSessionQuery(IQuery[Any]):
    body: WebScrapeRequestDto


class ValidateWebSessionHandler(IQueryHandler[ValidateWebSessionQuery, Any]):
    async def handle(self, query: ValidateWebSessionQuery) -> dict:
        body = query.body
        base_url = get_env_variable("SCHULNETZ_WEB_BASE_URL")
        cookies = {"PHPSESSID": body.session_id}

        is_valid = await validate_session(base_url, cookies, body.id, body.transid)
        return {"valid": is_valid, "message": "Session is active" if is_valid else "Session expired"}
