
import json
from typing import List, Optional
from fastapi import HTTPException, Response
from fastapi.responses import JSONResponse
import httpx
from src.application.services.env_service import get_env_variable

async def proxy_mobile_rest_query_async(token: str, target_url_path: str, method: str, query_params: Optional[List[tuple]] = None):
    target_url_path = f"/rest/v1/{target_url_path.lstrip('/')}"
    target_url = f"{get_env_variable("SCHULNETZ_API_BASE_URL")}{target_url_path}"

    request_headers = {
        "Referer": "https://schulnetz.web.app/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    params_to_forward = {}
    if query_params:
        for name, value in query_params:
            if value is not None:
                params_to_forward[name] = value

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