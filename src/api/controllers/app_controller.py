from fastapi import APIRouter
from src.application.queries.get_app_info_query import get_app_info_query_async

router = APIRouter()
router_tag = ["Application"]

@router.get("/api/app-info", tags=router_tag)
async def app_info():
    return await get_app_info_query_async()