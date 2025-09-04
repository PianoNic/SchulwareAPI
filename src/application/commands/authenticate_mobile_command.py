
from fastapi import HTTPException
from src.application.services import db_service
from src.application.dtos.auth_dto import MobileSessionDto
from src.api.auth import auth
from fastapi.logger import logger

async def authenticate_mobile_command_async(email: str, password: str):
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required for mobile authentication")
    
    try:
        logger.info(f"Performing mobile authentication for user: {email}")
        result = await auth.authenticate_with_credentials(email, password, "mobile")

        mobile_session_dto = MobileSessionDto(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            expires_in=3600
        )
        db_service.create_or_update_user(email, mobile_session_dto=mobile_session_dto)
        
        if result["success"] and result.get("access_token"):
            return {
                "success": True,
                "message": "Mobile API authentication successful",
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "token_type": "Bearer",
                "expires_in": 3600,
            }
        else:
            raise HTTPException(status_code=401, detail=result.get("error", "Mobile authentication failed"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mobile authentication error for {email}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Mobile authentication error: {str(e)}")