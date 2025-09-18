from fastapi import Request, HTTPException, Response
from src.application.commands.authenticate_mobile_command import authenticate_mobile_command_async
from src.application.commands.authenticate_web_command import authenticate_web_command_async
from src.application.commands.authenticate_unified_command import authenticate_unified_command_async
from src.api.router_registry import SchulwareAPIRouter, shared_limiter
from src.api.auth.auth import generate_oauth_url
from src.application.dtos.auth_oauth_dtos import (
    MobileOAuthUrlResponseDto,
    MobileCallbackRequestDto,
    MobileCallbackResponseDto,
    WebCallbackRequestDto,
    WebCallbackResponseDto
)
from src.application.dtos.authenticate_dtos import (
    AuthenticateRequestDto,
    AuthenticateMobileResponseDto
)
from src.infrastructure.logging_config import get_logger

router = SchulwareAPIRouter()
logger = get_logger("auth_controller")

@router.post("unified", response_model=AuthenticateMobileResponseDto)
@shared_limiter.limit("1/30seconds")
async def authenticate_unified_api(request: Request, auth_request: AuthenticateRequestDto):
    return await authenticate_unified_command_async(auth_request.email, auth_request.password)

@router.post("mobile", response_model=AuthenticateMobileResponseDto)
@shared_limiter.limit("1/30seconds")
async def authenticate_mobile_api(request: Request, auth_request: AuthenticateRequestDto):
    return await authenticate_mobile_command_async(auth_request.email, auth_request.password)

@router.post("web")
@shared_limiter.limit("1/30seconds")
async def authenticate_web_interface(request: Request, auth_request: AuthenticateRequestDto):
    return await authenticate_web_command_async(auth_request.email, auth_request.password)

@router.get("oauth/mobile/url", response_model=MobileOAuthUrlResponseDto)
@shared_limiter.limit("10/minute")
async def generate_mobile_oauth_url(request: Request):
    try:
        oauth_data = generate_oauth_url(auth_type="mobile", redirect_uri="")
        return MobileOAuthUrlResponseDto(
            authorization_url=oauth_data["auth_url"],
            code_verifier=oauth_data["code_verifier"]
        )
    except Exception as e:
        logger.error(f"Mobile OAuth URL generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# @router.get("oauth/web/url", response_model=str)
# @shared_limiter.limit("10/minute")
# async def generate_web_oauth_url(request: Request):
#     try:
#         oauth_data = generate_oauth_url(auth_type="web", redirect_uri="")
#         return Response(content=oauth_data["auth_url"], media_type="text/plain")
#     except Exception as e:
#         logger.error(f"Web OAuth URL generation error: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

@router.post("oauth/mobile/callback", response_model=MobileCallbackResponseDto)
@shared_limiter.limit("5/minute")
async def mobile_oauth_callback(request: Request, callback_data: MobileCallbackRequestDto):
    try:
        if callback_data.state:
            logger.info(f"Mobile callback with state: {callback_data.state[:10]}...")

        logger.info(f"Mobile callback: exchanging authorization code")
        access_token, refresh_token = await exchange_code_for_tokens(
            callback_data.code,
            callback_data.code_verifier
        )

        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to exchange authorization code for tokens")

        return MobileCallbackResponseDto(
            access_token=access_token,
            refresh_token=refresh_token
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mobile auth callback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# @router.post("oauth/web/callback", response_model=WebCallbackResponseDto)
# @shared_limiter.limit("5/minute")
# async def web_oauth_callback(request: Request, callback_data: WebCallbackRequestDto):
#     try:
#         logger.info(f"Web callback: processing authorization code")

#         return WebCallbackResponseDto(
#             success=True,
#             message="Web authentication callback processed successfully"
#         )

#     except Exception as e:
#         logger.error(f"Web auth callback error: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# Helper function for token exchange (imported from auth.py but made available here)
async def exchange_code_for_tokens(auth_code: str, code_verifier: str):
    """Exchange authorization code for tokens."""
    from src.api.auth.auth import exchange_code_for_tokens as _exchange
    return await _exchange(auth_code, code_verifier)