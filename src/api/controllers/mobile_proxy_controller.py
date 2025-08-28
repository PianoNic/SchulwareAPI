from fastapi import APIRouter, Query, Request, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from typing import List, Optional
import httpx
import json
from src.application.services.env_service import get_env_variable
from src.application.models.event import Event
from src.api.auth.token_dependency import get_current_token
from src.api.auth.bearer import security
from src.application.services.schulnetz_mobile_service import mobile_service
from src.application.services.token_service import token_service

router = APIRouter()
router_tag = ["Mobile API Proxy"]

SCHULNETZ_API_BASE_URL = get_env_variable("SCHULNETZ_API_BASE_URL")

async def proxy_mobile_rest(request: Request, token: str, target_url_path: str, method: str, allowed_query_params=None):
    """Proxy requests to Schulnetz mobile REST API"""
    if allowed_query_params is None:
        allowed_query_params = []
        
    target_url_path = f"/rest/v1/{target_url_path.lstrip('/')}"
    target_url = f"{SCHULNETZ_API_BASE_URL}{target_url_path}"
    
    request_headers = {
        "Referer": "https://schulnetz.web.app/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    params_to_forward = {}
    for param in allowed_query_params:
        if param in request.query_params:
            params_to_forward[param] = request.query_params[param]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                target_url,
                headers=request_headers,
                params=params_to_forward,
                content=None,
            )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code,
                headers={"Content-Type": content_type},
            )
        else:
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={"Content-Type": content_type},
            )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Mobile API error ({e.response.status_code}): {e.response.text}",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Network error or mobile API service unavailable: {e}",
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Mobile API returned malformed or non-JSON response.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected mobile API error occurred: {e}",
        )

@router.get("/api/mobile/userInfo", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_user_info(request: Request, token: str = Depends(get_current_token)):
    """Get user info from mobile API"""
    return await proxy_mobile_rest(request, token, "me", "GET")

@router.get("/api/mobile/settings", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_settings(request: Request, token: str = Depends(get_current_token)):
    """Get settings from mobile API"""
    return await proxy_mobile_rest(request, token, "config/settings", "GET")

@router.get("/api/mobile/agenda", tags=router_tag, dependencies=[Depends(security)], response_model=List[Event])
async def get_mobile_events(request: Request, token: str = Depends(get_current_token), 
                           min_date: Optional[str] = Query(None), max_date: Optional[str] = Query(None)):
    """Get events from mobile API"""
    return await proxy_mobile_rest(request, token, "me/events", "GET", allowed_query_params=["min_date", "max_date"])

@router.get("/api/mobile/absences", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_absences(request: Request, token: str = Depends(get_current_token)):
    """Get absences from mobile API"""
    return await proxy_mobile_rest(request, token, "me/absences", "GET")

@router.get("/api/mobile/absencenotices", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_absence_notices(request: Request, token: str = Depends(get_current_token)):
    """Get absence notices from mobile API"""
    return await proxy_mobile_rest(request, token, "me/absencenotices", "GET")

@router.get("/api/mobile/absenceNoticeStatus", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_absence_notice_status(request: Request, token: str = Depends(get_current_token)):
    """Get absence notice status from mobile API"""
    return await proxy_mobile_rest(request, token, "config/lists/absenceNoticeStatus", "GET")

@router.get("/api/mobile/exams", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_exams(request: Request, token: str = Depends(get_current_token)):
    """Get exams from mobile API"""
    return await proxy_mobile_rest(request, token, "me/exams", "GET")

@router.get("/api/mobile/grades", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_grades(request: Request, token: str = Depends(get_current_token)):
    """Get grades from mobile API"""
    return await proxy_mobile_rest(request, token, "me/grades", "GET")

@router.get("/api/mobile/notifications", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_notifications(request: Request, token: str = Depends(get_current_token)):
    """Get notifications from mobile API"""
    return await proxy_mobile_rest(request, token, "me/notifications/push", "GET")

@router.get("/api/mobile/topics", tags=router_tag, dependencies=[Depends(security)])
async def get_mobile_topics(request: Request, token: str = Depends(get_current_token)):
    """Get notification topics from mobile API"""
    return await proxy_mobile_rest(request, token, "me/notifications/topics", "GET")