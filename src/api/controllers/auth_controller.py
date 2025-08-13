import asyncio
import concurrent
from fastapi import APIRouter, Depends, Form, HTTPException, logger
from src.api.auth.auth import authenticate_with_credentials, two_fa_queue

log = logger.logger
router = APIRouter()
router_tag = ["Authorization"]

@router.post("/api/authenticate", tags=router_tag)
async def authenticate_and_get_token(email: str = Form(...), password: str = Form(...)):
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    
    try:
        result = await authenticate_with_credentials(email, password)
        if result.get("access_token") and result.get("refresh_token"):
            return {
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            }
        else:
            raise HTTPException(
            status_code=401,
            detail=result.get("error", "Authentication failed")
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")

@router.post("/api/2FA", tags=router_tag)
async def pass_2fa_token(two_fa: int = Form(...)):
    try:
        await two_fa_queue.put(two_fa)
        log.info(f"2FA token {two_fa} received and put in queue.")
        return {"message": "2FA token received. Processing authentication."}
    except Exception as e:
        log.error(f"Error processing 2FA token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing 2FA token: {str(e)}")