from fastapi import APIRouter, Depends, Request
from mediatorx import Mediator

from src.api.controller import controller
from src.api.dependencies import get_mediator
from src.api.rate_limit import shared_limiter
from src.application.dtos.app_info_dto import AppInfoDto
from src.application.queries.get_app_info_query import GetAppInfoQuery

router = APIRouter(prefix="/api/app", tags=["App"])

@controller(router)
class AppController:
    mediator: Mediator = Depends(get_mediator)

    @router.get("/app-info", response_model=AppInfoDto)
    @shared_limiter.limit("20/minute")
    async def app_info(self, request: Request):
        return await self.mediator.send(GetAppInfoQuery())
