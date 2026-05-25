from dataclasses import dataclass

from mediatorx import IQuery, IQueryHandler

from src.application.services.app_config_service import app_config
from src.application.dtos.app_info_dto import AppInfoDto

@dataclass
class GetAppInfoQuery(IQuery[AppInfoDto]):
    pass

class GetAppInfoHandler(IQueryHandler[GetAppInfoQuery, AppInfoDto]):
    async def handle(self, query: GetAppInfoQuery) -> AppInfoDto:
        return await get_app_info_query_async()

async def get_app_info_query_async() -> AppInfoDto:
    return AppInfoDto(
        version=app_config.get_version(),
        environment=app_config.get_environment()
    )
