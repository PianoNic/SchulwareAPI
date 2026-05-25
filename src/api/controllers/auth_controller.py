from fastapi import APIRouter, Depends, Form, Request, HTTPException
from mediatorx import Mediator

from src.api.auth.auth import generate_oauth_url
from src.api.controller import controller
from src.api.dependencies import get_mediator
from src.api.rate_limit import shared_limiter
from src.application.commands.authenticate_mobile_command import AuthenticateMobileCommand
from src.application.commands.authenticate_unified_command import AuthenticateUnifiedCommand
from src.application.commands.authenticate_web_command import AuthenticateWebCommand
from src.application.commands.refresh_token_command import RefreshTokenCommand
from src.application.dtos.auth_oauth_dtos import (
    MobileOAuthUrlResponseDto,
    MobileCallbackRequestDto,
    MobileCallbackResponseDto,
)
from src.application.dtos.authenticate_dtos import (
    AuthenticateRequestDto,
    AuthenticateMobileResponseDto,
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

    @router.post("/unified", response_model=AuthenticateMobileResponseDto)
    @shared_limiter.limit("1/30seconds")
    async def authenticate_unified(self, request: Request, body: AuthenticateRequestDto):
        return await self.mediator.send(AuthenticateUnifiedCommand(body.email, body.password))

    @router.post("/refresh", response_model=RefreshTokenResponseDto)
    @shared_limiter.limit("5/minute")
    async def refresh_token(self, request: Request, body: RefreshTokenRequestDto):
        """Stateless token + session refresh. Caller provides `context_state` from a
        prior call and receives an updated `context_state` to persist."""
        return await self.mediator.send(RefreshTokenCommand(body))

    @router.post("/mobile", response_model=AuthenticateMobileResponseDto)
    @shared_limiter.limit("1/30seconds")
    async def authenticate_mobile(self, request: Request, email: str = Form(...), password: str = Form(...)):
        return await self.mediator.send(AuthenticateMobileCommand(email, password))

    @router.post("/web")
    @shared_limiter.limit("1/30seconds")
    async def authenticate_web(self, request: Request, body: AuthenticateRequestDto):
        return await self.mediator.send(AuthenticateWebCommand(body.email, body.password))

    @router.get("/oauth/mobile/url", response_model=MobileOAuthUrlResponseDto)
    @shared_limiter.limit("10/minute")
    async def generate_mobile_oauth_url(self, request: Request):
        try:
            oauth_data = generate_oauth_url(auth_type="mobile", redirect_uri="")
            return MobileOAuthUrlResponseDto(
                authorization_url=oauth_data["auth_url"],
                code_verifier=oauth_data["code_verifier"],
            )
        except Exception as e:
            logger.error(f"Mobile OAuth URL generation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/oauth/mobile/callback", response_model=MobileCallbackResponseDto)
    @shared_limiter.limit("5/minute")
    async def mobile_oauth_callback(self, request: Request, callback_data: MobileCallbackRequestDto):
        try:
            if callback_data.state:
                logger.info(f"Mobile callback with state: {callback_data.state[:10]}...")

            logger.info("Mobile callback: exchanging authorization code")
            access_token, refresh_token = await _exchange_code_for_tokens(
                callback_data.code,
                callback_data.code_verifier,
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

async def _exchange_code_for_tokens(auth_code: str, code_verifier: str):
    from src.api.auth.auth import exchange_code_for_tokens as _exchange
    return await _exchange(auth_code, code_verifier)
