import asyncio
from datetime import datetime
from fastapi import APIRouter, Form, HTTPException, logger, Query
from src.api.auth.auth import authenticate_with_credentials, two_fa_queue
from src.application.services.token_service import token_service, ApplicationType

log = logger.logger
router = APIRouter()
router_tag = ["Authorization"]

@router.post("/api/authenticate/mobile", tags=router_tag)
async def authenticate_mobile_api(email: str = Form(...), password: str = Form(...)):
    """
    Authenticate user for mobile API access.
    Returns tokens for REST API calls.
    """
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    
    try:
        log.info(f"Performing full mobile authentication for user: {email}")
        result = await authenticate_with_credentials(email, password)
        
        if result.get("access_token") and result.get("refresh_token"):
            return {
                "success": True,
                "message": "Mobile API authentication successful with full login",
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "token_type": "Bearer",
                "expires_in": 3600,
                "app_type": ApplicationType.MOBILE_API,
                "source": "full_login"
            }
        else:
            raise HTTPException(
                status_code=401,
                detail=result.get("error", "Mobile authentication failed")
            )
            
    except Exception as e:
        log.error(f"Mobile authentication error for {email}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Mobile authentication error: {str(e)}")

@router.post("/api/authenticate/web", tags=router_tag)
async def authenticate_web_interface(email: str = Form(...), password: str = Form(...)):
    """
    Authenticate user for web interface access.
    Returns session information for web scraping.
    """
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    
    try:
        # No stored session logic, always perform full authentication
        log.info(f"Performing full web authentication for user: {email}")
        result = await authenticate_with_credentials(email, password)
        
        if result.get("access_token"):
            session_data = {
                "cookies": {
                    "PHPSESSID": "example_session_id",  # Extract from browser
                    "layout-size": "md",
                    "menuHidden": "0"
                },
                "extracted_at": str(datetime.now()),
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            return {
                "success": True,
                "message": "Web interface authentication successful",
                "access_token": result["access_token"],
                "session_data": session_data,
                "app_type": ApplicationType.WEB_INTERFACE,
                "source": "full_login"
            }
        else:
            raise HTTPException(
                status_code=401,
                detail=result.get("error", "Web authentication failed")
            )
            
    except Exception as e:
        log.error(f"Web authentication error for {email}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Web authentication error: {str(e)}")

@router.post("/api/2FA", tags=router_tag)
async def pass_2fa_token(two_fa: int = Form(...)):
    try:
        await two_fa_queue.put(two_fa)
        log.info(f"2FA token {two_fa} received and put in queue.")
        return {"message": "2FA token received. Processing authentication."}
    except Exception as e:
        log.error(f"Error processing 2FA token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing 2FA token: {str(e)}")