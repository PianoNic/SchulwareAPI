from dataclasses import dataclass

from mediatorx import IQuery, IQueryHandler

from src.application.dtos.app_info_dto import AppInfoDto
from src.application.services.app_config_service import app_config


@dataclass
class GetAppInfoQuery(IQuery[AppInfoDto]):
    pass


class GetAppInfoHandler(IQueryHandler[GetAppInfoQuery, AppInfoDto]):
    async def handle(self, query: GetAppInfoQuery) -> AppInfoDto:
        return AppInfoDto(
            version=app_config.get_version(),
            environment=app_config.get_environment(),
        )
