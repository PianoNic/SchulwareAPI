from fastapi import APIRouter, Form
from src.application.commands.authenticate_mobile_command import authenticate_mobile_command_async
from src.application.commands.authenticate_web_command import authenticate_web_command_async
from src.application.commands.authenticate_unified_command import authenticate_unified_command_async

router = APIRouter()
router_tag = ["Authorization"]

@router.post("/api/authenticate/unified", tags=router_tag)
async def authenticate_unified_api(email: str = Form(...), password: str = Form(...)):
    return await authenticate_unified_command_async(email, password)

@router.post("/api/authenticate/mobile", tags=router_tag)
async def authenticate_mobile_api(email: str = Form(...), password: str = Form(...)):
    return await authenticate_mobile_command_async(email, password)

@router.post("/api/authenticate/web", tags=router_tag)
async def authenticate_web_interface(email: str = Form(...), password: str = Form(...)):
    return await authenticate_web_command_async(email, password)

# @router.post("/api/2FA", tags=router_tag)
# async def pass_2fa_token(two_fa: int = Form(...)):
#     """Submit 2FA token during authentication flow."""
#     try:
#         await two_fa_queue.put(two_fa)
#         logger.info(f"2FA token {two_fa} received and put in queue.")
#         return {"message": "2FA token received. Processing authentication."}
#     except Exception as e:
#         logger.error(f"Error processing 2FA token: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Error processing 2FA token: {str(e)}")