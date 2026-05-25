from fastapi import Depends, Request
from mediatorx import Mediator

from src.api.dependencies import get_mediator
from src.api.router_registry import SchulwareAPIRouter, shared_limiter
from src.application.dtos.app_info_dto import AppInfoDto
from src.application.queries.get_app_info_query import GetAppInfoQuery

router = SchulwareAPIRouter()

@router.get("app-info", response_model=AppInfoDto)
@shared_limiter.limit("20/minute")
async def app_info(request: Request, mediator: Mediator = Depends(get_mediator)):
    return await mediator.send(GetAppInfoQuery())
