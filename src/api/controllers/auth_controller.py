from fastapi import APIRouter, Depends, Request
from mediatorx import Mediator

from src.api.controller import controller
from src.api.dependencies import get_mediator
from src.api.rate_limit import shared_limiter
from src.api.url_guard import validate_base_url
from src.application.commands.refresh_token_command import LoginCommand
from src.application.dtos.refresh_dtos import LoginRequestDto, LoginResponseDto

router = APIRouter(prefix="/api/authenticate", tags=["Auth"])


@controller(router)
class AuthController:
    mediator: Mediator = Depends(get_mediator)

    @router.post("/login", response_model=LoginResponseDto)
    @shared_limiter.limit("5/minute")
    async def login(self, request: Request, body: LoginRequestDto):
        """Unified Schulnetz auth — one endpoint for every sign-in path.

        Pass `session_cookies` from a previous response for a silent passwordless
        re-auth, and/or `email` + `password` (+ `totp_secret`/`totp_code`) for a
        headless credential login. When both are present the cookies are tried
        first and the credentials are the fallback. No browser, no WebView.

        Returns mobile tokens, the web session (PHPSESSID + id/transid), and the
        rotated `session_cookies` to persist for the next call.
        """
        return await self.mediator.send(LoginCommand(
            schulnetz_base_url=validate_base_url(body.schulnetz_base_url),
            session_cookies=body.session_cookies,
            email=body.email,
            password=body.password,
            totp_secret=body.totp_secret,
            totp_code=body.totp_code,
            user_agent=body.user_agent,
        ))
