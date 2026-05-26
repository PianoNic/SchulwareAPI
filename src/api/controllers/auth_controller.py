from fastapi import APIRouter, Depends, HTTPException, Request
from mediatorx import Mediator

from src.api.auth.auth import generate_oauth_url
from src.api.controller import controller
from src.api.dependencies import get_mediator, get_schulnetz_base_url
from src.api.rate_limit import shared_limiter
from src.application.commands.refresh_token_command import RefreshTokenCommand
from src.application.dtos.auth_oauth_dtos import (
    MobileCallbackRequestDto,
    MobileCallbackResponseDto,
    MobileOAuthUrlResponseDto,
)
from src.application.dtos.refresh_dtos import (
    RefreshTokenRequestDto,
    RefreshTokenResponseDto,
)
from src.infrastructure.logging_config import get_logger

router = APIRouter(prefix="/api/authenticate", tags=["Auth"])
logger = get_logger("auth_controller")


@controller(router)
class AuthController:
    mediator: Mediator = Depends(get_mediator)

    @router.post("/refresh", response_model=RefreshTokenResponseDto)
    @shared_limiter.limit("5/minute")
    async def refresh_token(self, request: Request, body: RefreshTokenRequestDto):
        """Stateless token + session refresh. Caller provides `context_state` from a
        prior call and receives an updated `context_state` to persist."""
        return await self.mediator.send(RefreshTokenCommand(body))

    @router.get("/oauth/mobile/url", response_model=MobileOAuthUrlResponseDto)
    @shared_limiter.limit("10/minute")
    async def generate_mobile_oauth_url(
        self,
        request: Request,
        base_url: str = Depends(get_schulnetz_base_url),
    ):
        try:
            oauth_data = generate_oauth_url(base_url=base_url, auth_type="mobile", redirect_uri="")
            return MobileOAuthUrlResponseDto(
                authorization_url=oauth_data["auth_url"],
                code_verifier=oauth_data["code_verifier"],
            )
        except Exception as e:
            logger.error(f"Mobile OAuth URL generation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/oauth/mobile/callback", response_model=MobileCallbackResponseDto)
    @shared_limiter.limit("5/minute")
    async def mobile_oauth_callback(
        self,
        request: Request,
        callback_data: MobileCallbackRequestDto,
        base_url: str = Depends(get_schulnetz_base_url),
    ):
        try:
            if callback_data.state:
                logger.info(f"Mobile callback with state: {callback_data.state[:10]}...")

            logger.info("Mobile callback: exchanging authorization code")
            access_token, refresh_token = await _exchange_code_for_tokens(
                callback_data.code,
                callback_data.code_verifier,
                base_url,
            )

            if not access_token:
                raise HTTPException(status_code=400, detail="Failed to exchange authorization code for tokens")

            return MobileCallbackResponseDto(
                access_token=access_token,
                refresh_token=refresh_token,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Mobile auth callback error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


async def _exchange_code_for_tokens(auth_code: str, code_verifier: str, base_url: str):
    from src.api.auth.auth import exchange_code_for_tokens as _exchange
    return await _exchange(auth_code, code_verifier, base_url)
