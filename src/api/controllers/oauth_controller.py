from src.application.queries import get_mobile_oauth_url_query
from src.application.services.oauth_service import generate_oauth_url
from src.api.router_registry import SchulwareAPIRouter, shared_limiter
from src.infrastructure.logging_config import get_logger
from src.application.dtos.auth_oauth_dtos import MobileOAuthUrlResponseDto, MobileCallbackRequestDto, MobileCallbackResponseDto
from fastapi import Request, HTTPException, Response
from src.api.auth.auth import exchange_code_for_tokens

router = SchulwareAPIRouter()
logger = get_logger("oauth_controller")

@router.get("mobile/url", response_model=MobileOAuthUrlResponseDto)
@shared_limiter.limit("1/second")
async def generate_mobile_oauth_url(request: Request):
    try:
        return get_mobile_oauth_url_query.get_mobile_oauth_url_query()
    except Exception as e:
        logger.error(f"Mobile OAuth URL generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("oauth/web/url", response_model=str)
@shared_limiter.limit("1/second")
async def generate_web_oauth_url(request: Request):
    try:
        oauth_data = generate_oauth_url(auth_type="web", redirect_uri="")
        return Response(content=oauth_data["auth_url"], media_type="text/plain")
    except Exception as e:
        logger.error(f"Web OAuth URL generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("mobile/callback", response_model=MobileCallbackResponseDto)
@shared_limiter.limit("1/second")
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