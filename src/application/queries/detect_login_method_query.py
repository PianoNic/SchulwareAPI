from dataclasses import dataclass

from mediatorx import IQuery, IQueryHandler

from src.application.dtos.refresh_dtos import LoginMethodDto
from src.application.services.native_login_service import detect_login_mode


@dataclass
class DetectLoginMethodQuery(IQuery[LoginMethodDto]):
    base_url: str
    user_agent: str | None = None


class DetectLoginMethodHandler(IQueryHandler[DetectLoginMethodQuery, LoginMethodDto]):
    async def handle(self, query: DetectLoginMethodQuery) -> LoginMethodDto:
        return LoginMethodDto(method=await detect_login_mode(query.base_url.rstrip("/"), query.user_agent))
