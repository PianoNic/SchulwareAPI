from src.application.services.app_config_service import app_config
from src.application.dtos.app_info_dto import AppInfoDto

async def get_app_info_query_async() -> AppInfoDto:
    return AppInfoDto(
        version=app_config.get_version(),
        environment=app_config.get_environment()
    )