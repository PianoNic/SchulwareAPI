from fastapi import APIRouter, Form, HTTPException, logger, Query
from src.api.auth.auth import (
    authenticate_unified_webapp_flow,
    authenticate_unified_with_navigation_listener, 
    authenticate_with_existing_session,
    authenticate_with_credentials, 
    two_fa_queue
)
from src.application.services.token_service import token_service, ApplicationType

log = logger.logger
router = APIRouter()
router_tag = ["Authorization"]

@router.post("/api/authenticate/unified", tags=router_tag)
async def authenticate_unified_api(email: str = Form(...), password: str = Form(...)):
    """
    Unified authentication endpoint that provides both mobile OAuth2 tokens 
    and web session cookies in a single Microsoft login flow.
    
    This handles both schulnetz.bbbaden.ch and schulnetz.web.app redirect flows.
    """
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    
    try:
        log.info(f"Performing unified authentication for user: {email}")
        
        # Try the navigation listener approach first
        result = await authenticate_unified_with_navigation_listener(email, password)
        
        # If that fails, try the response listener approach
        if not result["success"]:
            log.info("Navigation listener approach failed, trying response listener...")
            result = await authenticate_unified_webapp_flow(email, password)
        
        if result["success"]:
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
                    "noten_url": result["noten_url"],
                    "auth_code": result["auth_code"]
                },
                # Metadata
                "session_types": result["session_types"],
                "authenticated_at": result["authenticated_at"],
                "redirect_domain": result.get("redirect_domain", "unknown"),
                "app_types": [ApplicationType.MOBILE_API, ApplicationType.WEB_INTERFACE]
            }
        else:
            raise HTTPException(
                status_code=401,
                detail=result.get("error", "Unified authentication failed")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Unified authentication error for {email}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unified authentication error: {str(e)}")

@router.post("/api/authenticate/mobile", tags=router_tag)
async def authenticate_mobile_api(
    email: str = Form(None), 
    password: str = Form(None),
    use_existing_session: bool = Form(False)
):
    """
    Authenticate user for mobile API access.
    
    Args:
        email: Microsoft account email (required if not using existing session)
        password: Microsoft account password (required if not using existing session)  
        use_existing_session: Try to use existing session cookies from token service
    """
    
    # Try existing session first if requested
    if use_existing_session:
        try:
            existing_session = token_service.get_session_data(email or "unknown")
            if existing_session and existing_session.get("session_cookies"):
                log.info("Attempting mobile auth with existing session cookies...")
                
                # Note: This will likely fail since mobile tokens can't be refreshed from cookies
                # But we try anyway and fall back to full auth
                result = await authenticate_with_existing_session(
                    existing_session["session_cookies"], 
                    "mobile"
                )
                
                if result["success"]:
                    return {
                        "success": True,
                        "message": "Mobile API authentication successful with existing session",
                        "access_token": result.get("access_token"),
                        "refresh_token": result.get("refresh_token"),
                        "token_type": "Bearer",
                        "expires_in": 3600,
                        "app_type": ApplicationType.MOBILE_API,
                        "source": "existing_session"
                    }
        except Exception as e:
            log.info(f"Existing session attempt failed: {e}")
    
    # Full authentication required
    if not email or not password:
        raise HTTPException(
            status_code=400, 
            detail="Email and password are required for mobile authentication"
        )
    
    try:
        log.info(f"Performing mobile authentication for user: {email}")
        result = await authenticate_with_credentials(email, password, "mobile")

        if result["success"] and result.get("access_token"):
            return {
                "success": True,
                "message": "Mobile API authentication successful",
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
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Mobile authentication error for {email}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Mobile authentication error: {str(e)}")


@router.post("/api/authenticate/web", tags=router_tag)
async def authenticate_web_interface(
    email: str = Form(None), 
    password: str = Form(None),
    use_existing_session: bool = Form(False)
):
    """
    Authenticate user for web interface access.
    
    Args:
        email: Microsoft account email (required if not using existing session)
        password: Microsoft account password (required if not using existing session)
        use_existing_session: Try to use existing session cookies from token service
    """
    
    # Try existing session first if requested
    if use_existing_session:
        try:
            existing_session = token_service.get_session_data(email or "unknown")
            if existing_session and existing_session.get("session_cookies"):
                log.info("Attempting web auth with existing session cookies...")
                
                result = await authenticate_with_existing_session(
                    existing_session["session_cookies"], 
                    "web"
                )
                
                if result["success"]:
                    return {
                        "success": True,
                        "message": "Web interface authentication successful with existing session",
                        "session_cookies": result["session_cookies"],
                        "navigation_urls": result["navigation_urls"],
                        "noten_url": result["noten_url"],
                        "app_type": ApplicationType.WEB_INTERFACE,
                        "source": "existing_session"
                    }
        except Exception as e:
            log.info(f"Existing session attempt failed: {e}")
    
    # Full authentication required
    if not email or not password:
        raise HTTPException(
            status_code=400, 
            detail="Email and password are required for web authentication"
        )
    
    try:
        log.info(f"Performing web authentication for user: {email}")
        result = await authenticate_with_credentials(email, password, "web")
        
        if result["success"]:
            return {
                "success": True,
                "message": "Web interface authentication successful",
                "session_cookies": result["session_cookies"],
                "navigation_urls": result.get("navigation_urls", {}),
                "noten_url": result.get("noten_url"),
                "auth_code": result.get("auth_code"),
                "app_type": ApplicationType.WEB_INTERFACE,
                "source": "full_login"
            }
        else:
            raise HTTPException(
                status_code=401,
                detail=result.get("error", "Web authentication failed")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Web authentication error for {email}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Web authentication error: {str(e)}")


@router.post("/api/2FA", tags=router_tag)
async def pass_2fa_token(two_fa: int = Form(...)):
    """Submit 2FA token during authentication flow."""
    try:
        await two_fa_queue.put(two_fa)
        log.info(f"2FA token {two_fa} received and put in queue.")
        return {"message": "2FA token received. Processing authentication."}
    except Exception as e:
        log.error(f"Error processing 2FA token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing 2FA token: {str(e)}")


@router.get("/api/session/validate", tags=router_tag)
async def validate_session(email: str = Query(...)):
    """
    Validate existing session without full authentication.
    """
    try:
        existing_session = token_service.get_session_data(email)
        if not existing_session:
            return {
                "valid": False,
                "message": "No existing session found",
                "requires_auth": True
            }
        
        session_cookies = existing_session.get("session_cookies")
        if session_cookies:
            result = await authenticate_with_existing_session(session_cookies, "web")
            
            return {
                "valid": result["success"],
                "message": result.get("message", "Session validation completed"),
                "requires_auth": not result["success"],
                "session_data": result if result["success"] else None
            }
        else:
            return {
                "valid": False,
                "message": "No session cookies available",
                "requires_auth": True
            }
            
    except Exception as e:
        log.error(f"Session validation error: {e}")
        return {
            "valid": False,
            "message": f"Session validation error: {str(e)}",
            "requires_auth": True
        }