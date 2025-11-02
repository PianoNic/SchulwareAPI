import json
from typing import List, Optional
from fastapi import HTTPException, Response
from fastapi.responses import JSONResponse
import httpx
from src.application.services.env_service import get_env_variable
from src.application.services.test_token_config import is_test_token, get_mock_data
from src.infrastructure.logging_config import get_logger
from src.infrastructure.monitoring import monitor_performance, add_breadcrumb, capture_exception

logger = get_logger("mobile_proxy")

@monitor_performance("mobile.proxy.request")
async def proxy_mobile_rest_query_async(token: str, target_url_path: str, method: str, query_params: Optional[List[tuple]] = None):
    # Check if this is a test token - return mock data
    if is_test_token(token):
        logger.info(f"Test token detected - returning mock data for: {target_url_path}")

        # Normalize the path
        normalized_path = f"/rest/v1/{target_url_path.lstrip('/')}"

        # Map endpoints to mock data types
        # Handle endpoints with path parameters like /rest/v1/me/cockpitReport/{id}
        endpoint_map = {
            "/rest/v1/me": "user_info",
            "/rest/v1/config/settings": "settings",
            "/rest/v1/me/events": "events",
            "/rest/v1/me/absences": "absences",
            "/rest/v1/me/absencenotices": "absencenotices",
            "/rest/v1/config/lists/absenceNoticeStatus": "absencenoticestatus",
            "/rest/v1/me/exams": "exams",
            "/rest/v1/me/grades": "grades",
            "/rest/v1/me/notifications/push": "notifications",
            "/rest/v1/me/notifications/topics": "topics",
            "/rest/v1/me/lateness": "lateness",
        }

        # Try exact match first
        data_type = endpoint_map.get(normalized_path)

        # If no exact match, check for parameterized endpoints
        if not data_type:
            if "/me/cockpitReport/" in normalized_path:
                # Extract report ID from path
                parts = normalized_path.split("/")
                report_id = int(parts[-1]) if parts[-1].isdigit() else 1
                mock_response = get_mock_data("cockpitreport", report_id=report_id)
                return JSONResponse(content=mock_response, status_code=200)
            else:
                # Default to events for unknown endpoints
                data_type = "events"

        mock_response = get_mock_data(data_type)
        return JSONResponse(content=mock_response, status_code=200)

    target_url_path = f"/rest/v1/{target_url_path.lstrip('/')}"
    base_url = get_env_variable("SCHULNETZ_API_BASE_URL")
    target_url = f"{base_url}{target_url_path}"

    add_breadcrumb(
        message=f"Mobile API proxy: {method} {target_url_path}",
        category="mobile.proxy",
        level="info",
        data={"method": method, "path": target_url_path}
    )

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
        capture_exception(
            e,
            context={
                "api_type": "mobile_proxy",
                "method": method,
                "path": target_url_path,
                "status_code": e.response.status_code
            },
            level="warning"
        )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Mobile API error ({e.response.status_code}): {e.response.text}",
        )
    except httpx.RequestError as e:
        capture_exception(
            e,
            context={
                "api_type": "mobile_proxy",
                "method": method,
                "path": target_url_path,
                "error_type": "network_error"
            },
            level="error"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Network error or mobile API service unavailable: {e}",
        )
    except json.JSONDecodeError as e:
        capture_exception(
            e,
            context={
                "api_type": "mobile_proxy",
                "method": method,
                "path": target_url_path,
                "error_type": "json_decode_error"
            },
            level="error"
        )
        raise HTTPException(
            status_code=500,
            detail="Mobile API returned malformed or non-JSON response.",
        )
    except Exception as e:
        capture_exception(
            e,
            context={
                "api_type": "mobile_proxy",
                "method": method,
                "path": target_url_path,
                "error_type": type(e).__name__
            },
            level="error"
        )
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected mobile API error occurred: {e}",
        )