from fastapi import HTTPException
from fastapi.logger import logger
from src.application.dtos.web.web_urls_dto import WebUrlsDto
from src.application.services import db_service
from src.application.dtos.auth_dto import MobileSessionDto, WebSessionDto
from src.api.auth import auth

async def authenticate_unified_command_async(email: str, password: str):
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    try:
        logger.info(f"Performing unified authentication for user: {email}")
        
        # Try the navigation listener approach first
        result = await auth.authenticate_unified(email, password)

        if result["success"]:
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
            raise HTTPException(
                status_code=401,
                detail=result.get("error", "Unified authentication failed")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unified authentication error for {email}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unified authentication error: {str(e)}")