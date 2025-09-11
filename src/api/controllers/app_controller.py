from src.application.queries.get_app_info_query import get_app_info_query_async
from src.application.dtos.app_info_dto import AppInfoDto
from src.api.router_registry import SchulwareAPIRouter, shared_limiter
from fastapi import Request

router = SchulwareAPIRouter()

@router.get("app-info", response_model=AppInfoDto)
@shared_limiter.limit("20/minute")
async def app_info(request: Request):
    return await get_app_info_query_async()