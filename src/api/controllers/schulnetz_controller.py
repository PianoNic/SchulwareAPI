from fastapi import APIRouter, Query, Request, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from typing import Optional
import httpx
import json
from src.api.services.env_service import get_env_variable
from src.api.auth.token_dependency import get_current_token
from src.api.auth.bearer import security

router = APIRouter()
router_tag = ["Schulnetz Proxy"]

SCHULNETZ_API_BASE_URL = get_env_variable("SCHULNETZ_API_BASE_URL")

async def proxy_schulnetz_rest(request: Request, token: str, target_url_path: str, method: str, allowed_query_params=None):
    if allowed_query_params is None:
        allowed_query_params = []
    target_base_url = None
    request_headers = {}

    target_url_path = f"/rest/v1/{target_url_path.lstrip('/')}"
    target_base_url = SCHULNETZ_API_BASE_URL
    request_headers = {
        "Referer": "https://schulnetz.web.app/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    target_url = f"{target_base_url}{target_url_path}"
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
            detail=f"Upstream API error ({e.response.status_code}): {e.response.text}",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Network error or upstream service unavailable: {e}",
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Upstream API returned malformed or non-JSON response.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {e}",
        )

@router.get("/api/userInfo", tags=router_tag, dependencies=[Depends(security)])
async def get_me(request: Request, token: str = Depends(get_current_token)):
    return await proxy_schulnetz_rest(request, token, "me", "GET")

@router.get("/api/settings", tags=router_tag, dependencies=[Depends(security)])
async def get_settings(request: Request, token: str = Depends(get_current_token)):
    return await proxy_schulnetz_rest(request, token, "config/settings", "GET")

@router.get("/api/agenda", tags=router_tag, dependencies=[Depends(security)])
async def get_me_events(request: Request, token: str = Depends(get_current_token), min_date: Optional[str] = Query(None), max_date: Optional[str] = Query(None)):
    return await proxy_schulnetz_rest(request, token, "me/events", "GET", allowed_query_params=["min_date", "max_date"])

@router.get("/api/absences", tags=router_tag, dependencies=[Depends(security)])
async def get_me_absences(request: Request, token: str = Depends(get_current_token)):
    return await proxy_schulnetz_rest(request, token, "me/absences", "GET")

@router.get("/api/absencenotices", tags=router_tag, dependencies=[Depends(security)])
async def get_me_absencenotices(request: Request, token: str = Depends(get_current_token)):
    return await proxy_schulnetz_rest(request, token, "me/absencenotices", "GET")

@router.get("/api/absenceNoticeStatus", tags=router_tag, dependencies=[Depends(security)])
async def get_absence_notice_status(request: Request, token: str = Depends(get_current_token)):
    return await proxy_schulnetz_rest(request, token, "config/lists/absenceNoticeStatus", "GET")

@router.get("/api/exams", tags=router_tag, dependencies=[Depends(security)])
async def get_me_exams(request: Request, token: str = Depends(get_current_token)):
    return await proxy_schulnetz_rest(request, token, "me/exams", "GET")

@router.get("/api/grades", tags=router_tag, dependencies=[Depends(security)])
async def get_me_grades(request: Request, token: str = Depends(get_current_token)):
    return await proxy_schulnetz_rest(request, token, "me/grades", "GET")

@router.get("/api/notifications", tags=router_tag, dependencies=[Depends(security)])
async def get_me_notifications_push(request: Request, token: str = Depends(get_current_token)):
    return await proxy_schulnetz_rest(request, token, "me/notifications/push", "GET")

@router.get("/api/topics", tags=router_tag, dependencies=[Depends(security)])
async def get_me_notifications_topics(request: Request, token: str = Depends(get_current_token)):
    return await proxy_schulnetz_rest(request, token, "me/notifications/topics", "GET")
