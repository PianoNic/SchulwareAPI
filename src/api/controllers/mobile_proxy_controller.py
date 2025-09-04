from fastapi import APIRouter, Query, Depends
from typing import List, Optional
from src.application.queries.proxy_mobile_rest_query import proxy_mobile_rest_query_async
from src.api.auth.token_dependency import get_current_token
from src.application.models.event import Event
from src.api.auth.bearer import security

router = APIRouter()
router_tag = ["Mobile API"]

@router.get("/api/mobile/userInfo", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_user_info(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me", "GET")

@router.get("/api/mobile/settings", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_settings(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "config/settings", "GET")

@router.get("/api/mobile/agenda", tags=router_tag, dependencies=[Depends(security)], response_model=List[Event])
async def get_mobile_events(token: str = Depends(get_current_token), min_date: Optional[str] = Query(None), max_date: Optional[str] = Query(None)):
    query_params = [("min_date", min_date), ("max_date", max_date)]
    return await proxy_mobile_rest_query_async(token, "me/events", "GET", query_params=query_params)

@router.get("/api/mobile/absences", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_absences(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/absences", "GET")

@router.get("/api/mobile/absencenotices", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_absence_notices(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/absencenotices", "GET")

@router.get("/api/mobile/absenceNoticeStatus", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_absence_notice_status( token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "config/lists/absenceNoticeStatus", "GET")

@router.get("/api/mobile/exams", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_exams(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/exams", "GET")

@router.get("/api/mobile/grades", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_grades(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/grades", "GET")

@router.get("/api/mobile/notifications", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_notifications(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/notifications/push", "GET")

@router.get("/api/mobile/topics", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_topics(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/notifications/topics", "GET")

@router.get("/api/mobile/lateness", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_lateness(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/lateness", "GET")

@router.get("/api/mobile/cockpitReport/{report_id}", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_cockpit_report(report_id: int, token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, f"me/cockpitReport/{report_id}", "GET")