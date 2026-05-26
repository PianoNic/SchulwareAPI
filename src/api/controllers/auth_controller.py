from fastapi import APIRouter, Depends, HTTPException, Request
from mediatorx import Mediator

from src.api.auth.auth import generate_oauth_url
from src.api.controller import controller
from src.api.dependencies import get_mediator, get_schulnetz_base_url
from src.api.rate_limit import shared_limiter
from src.application.commands.refresh_token_command import RefreshTokenCommand
from src.application.commands.refresh_token_grant_command import RefreshTokenGrantCommand
from src.application.dtos.auth_oauth_dtos import (
    MobileCallbackRequestDto,
    MobileCallbackResponseDto,
    MobileOAuthUrlResponseDto,
)
from src.application.dtos.refresh_dtos import (
    RefreshTokenGrantRequestDto,
    RefreshTokenGrantResponseDto,
    RefreshTokenRequestDto,
    RefreshTokenResponseDto,
    RefreshTokenWithCredentialsRequestDto,
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
        """Stateless token + session refresh using a stored browser context.

        Caller provides `context_state` from a prior call and receives an
        updated `context_state` to persist. No credentials are sent. If the
        stored context has expired, re-authenticate via
        `/api/authenticate/oauth/mobile/url`."""
        return await self.mediator.send(RefreshTokenCommand(
            schulnetz_base_url=body.schulnetz_base_url,
            context_state=body.context_state,
            user_agent=body.user_agent,
        ))

    @router.post(
        "/refresh-token",
        response_model=RefreshTokenGrantResponseDto,
        description=(
            "## ⚗️ EXPERIMENTAL — spike for [#121]"
            "(https://github.com/PianoNic/SchulwareAPI/issues/121)\n\n"
            "Direct OAuth2 **refresh_token grant** against `/token.php` — no "
            "Playwright, no Chromium, milliseconds per call. If Schulnetz "
            "honours this grant, it becomes the preferred refresh path and "
            "`/refresh` (context_state replay) only stays around as a "
            "fallback.\n\n"
            "**Requires** a `refresh_token` from an authorization flow that "
            "included the `offline_access` scope. This branch enables that "
            "scope at every OAuth call site, so any token captured after "
            "deploying it qualifies.\n\n"
            "**Do not rely on this in production yet** — it's here to be "
            "tested. The response includes the raw `/token.php` body in "
            "`raw_response` so you can inspect exactly what Schulnetz returns."
        ),
    )
    @shared_limiter.limit("10/minute")
    async def refresh_with_grant(
        self,
        request: Request,
        body: RefreshTokenGrantRequestDto,
    ):
        return await self.mediator.send(RefreshTokenGrantCommand(
            schulnetz_base_url=body.schulnetz_base_url.rstrip("/"),
            refresh_token=body.refresh_token,
        ))

    @router.post(
        "/refresh-with-credentials",
        response_model=RefreshTokenResponseDto,
        deprecated=True,
        description=(
            "## ⚠️ DEPRECATED — DO NOT USE\n\n"
            "Refreshes tokens by replaying a **full Microsoft SSO login with raw "
            "credentials** through a headless browser. Provided only as a "
            "last-resort fallback for the very first refresh after cold-start.\n\n"
            "**Use `/api/authenticate/refresh` with a stored `context_state` "
            "for every subsequent call.** Storing the user's password long-term "
            "to call this endpoint repeatedly defeats the entire stateless "
            "design and exposes the credentials unnecessarily.\n\n"
            "Preferred cold-start path: drive the OAuth flow via "
            "`/api/authenticate/oauth/mobile/url` and capture `context_state` "
            "from the resulting browser session, then use `/refresh` from "
            "then on."
        ),
    )
    @shared_limiter.limit("2/minute")
    async def refresh_with_credentials(
        self, request: Request, body: RefreshTokenWithCredentialsRequestDto
    ):
        return await self.mediator.send(RefreshTokenCommand(
            schulnetz_base_url=body.schulnetz_base_url,
            email=body.email,
            password=body.password,
            user_agent=body.user_agent,
        ))

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
