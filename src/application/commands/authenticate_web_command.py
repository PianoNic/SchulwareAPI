from fastapi import HTTPException
from fastapi.logger import logger
from src.application.dtos.auth_dto import WebSessionDto
from src.application.services import db_service
from src.api.auth import auth

async def authenticate_web_command_async(email: str, password: str):
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required for web authentication")
    
    try:
        logger.info(f"Performing web authentication for user: {email}")
        result = await auth.authenticate_with_credentials(email, password, "web")

        web_session_dto = WebSessionDto(
            php_session_id=result["auth_code"]
        )
        db_service.create_or_update_user(email, web_session_dto=web_session_dto)

        if result["success"]:
            return {
                "success": True,
                "message": "Web interface authentication successful",
                "session_cookies": result["session_cookies"],
                "navigation_urls": result.get("navigation_urls", {}),
                "auth_code": result.get("auth_code"),
            }
        else:
            raise HTTPException(
                status_code=401,
                detail=result.get("error", "Web authentication failed")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Web authentication error for {email}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Web authentication error: {str(e)}")