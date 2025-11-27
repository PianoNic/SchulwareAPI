from fastapi import HTTPException
from src.infrastructure.logging_config import get_logger
from src.infrastructure.monitoring import (
    capture_exception,
    add_breadcrumb,
    set_user_context,
    monitor_performance,
    set_context
)
from src.application.dtos.web.web_urls_dto import WebUrlsDto
from src.application.services import db_service
from src.application.dtos.auth_dto import MobileSessionDto, WebSessionDto
from src.api.auth import auth

logger = get_logger("unified_auth")

@monitor_performance("authentication.unified")
async def authenticate_unified_command_async(email: str, password: str):
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    # Set user context for error tracking
    set_user_context(email=email)
    add_breadcrumb(
        message=f"Starting unified authentication for user: {email}",
        category="auth",
        level="info"
    )

    try:
        logger.info(f"Performing unified authentication for user: {email}")

        # Try the navigation listener approach first
        add_breadcrumb(
            message="Attempting navigation listener approach",
            category="auth",
            level="info"
        )
        result = await auth.authenticate_unified(email, password)

        # If that fails, try the response listener approach
        if not result["success"]:
            logger.info("Navigation listener approach failed, trying response listener...")
            add_breadcrumb(
                message="Navigation listener failed, trying response listener",
                category="auth",
                level="warning"
            )
            result = await auth.authenticate_unified_webapp_flow(email, password)

        if result["success"]:
            add_breadcrumb(
                message="Authentication successful",
                category="auth",
                level="info"
            )
            mobile_session_dto = MobileSessionDto(
                access_token=result["access_token"],
                refresh_token=result["refresh_token"],
                expires_in=3600
            )
            web_session_dto = WebSessionDto(
                php_session_id=result["auth_code"],
            )
            web_url_dto = WebUrlsDto(
                absent_notices=result["navigation_urls"]["Absenzen"],
                agenda=result["navigation_urls"]["Agenda"],
                documents=result["navigation_urls"]["Listen&Dokumente"],
                grades=result["navigation_urls"]["Noten"],
                lesson=result["navigation_urls"]["Unterricht"],
                start=result["navigation_urls"]["Start"],
                student_id_card=result["navigation_urls"]["Ausweis"]
            )
            db_service.create_or_update_user(email, mobile_session_dto=mobile_session_dto, web_session_dto=web_session_dto, web_url_dto=web_url_dto)

            # Set context for successful authentication
            set_context("auth_result", {
                "success": True,
                "method": "unified",
                "user": email
            })

            return {
                "success": True,
                "message": "Unified authentication successful",
                # Mobile API access
                "mobile": {
                    "access_token": result["access_token"],
                    "refresh_token": result["refresh_token"],
                    "token_type": "Bearer",
                    "expires_in": 3600
                },
                # Web interface access
                "web": {
                    "session_cookies": result["session_cookies"],
                    "navigation_urls": result["navigation_urls"],
                    "auth_code": result["auth_code"]
                }
            }
        else:
            error_detail = result.get("error", "Unified authentication failed")
            add_breadcrumb(
                message=f"Authentication failed: {error_detail}",
                category="auth",
                level="error",
                data={"error": error_detail}
            )
            raise HTTPException(
                status_code=401,
                detail=error_detail
            )

    except HTTPException as he:
        # Capture authentication failures
        capture_exception(
            he,
            context={
                "auth_type": "unified",
                "user": email,
                "status_code": he.status_code
            },
            level="warning"
        )
        raise
    except Exception as e:
        logger.error(f"Unified authentication error for {email}: {str(e)}")
        # Capture unexpected errors
        capture_exception(
            e,
            context={
                "auth_type": "unified",
                "user": email,
                "error_type": type(e).__name__
            },
            level="error"
        )
        raise HTTPException(status_code=500, detail=f"Unified authentication error: {str(e)}")