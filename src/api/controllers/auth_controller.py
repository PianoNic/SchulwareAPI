from fastapi import Form, Request
from src.application.commands.authenticate_mobile_command import authenticate_mobile_command_async
from src.application.commands.authenticate_web_command import authenticate_web_command_async
from src.application.commands.authenticate_unified_command import authenticate_unified_command_async
from src.api.router_registry import SchulwareAPIRouter, shared_limiter

router = SchulwareAPIRouter()

@router.post("unified")
@shared_limiter.limit("1/30seconds")
async def authenticate_unified_api(request: Request, email: str = Form(...), password: str = Form(...)):
    return await authenticate_unified_command_async(email, password)

@router.post("mobile")
@shared_limiter.limit("1/30seconds")
async def authenticate_mobile_api(request: Request, email: str = Form(...), password: str = Form(...)):
    return await authenticate_mobile_command_async(email, password)

@router.post("web")
@shared_limiter.limit("1/30seconds")
async def authenticate_web_interface(request: Request, email: str = Form(...), password: str = Form(...)):
    return await authenticate_web_command_async(email, password)

# @router.post("/api/2FA")
# async def pass_2fa_token(two_fa: int = Form(...)):
#     """Submit 2FA token during authentication flow."""
#     try:
#         await two_fa_queue.put(two_fa)
#         logger.info(f"2FA token {two_fa} received and put in queue.")
#         return {"message": "2FA token received. Processing authentication."}
#     except Exception as e:
#         logger.error(f"Error processing 2FA token: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Error processing 2FA token: {str(e)}") 