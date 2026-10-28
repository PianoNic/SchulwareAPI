from fastapi import APIRouter, Depends, Request
from mediatorx import Mediator

from src.api.controller import controller
from src.api.dependencies import get_mediator, get_schulnetz_base_url
from src.api.rate_limit import is_service_caller, require_service_key, shared_limiter
from src.api.url_guard import validate_base_url
from src.application.commands.browser_login_command import CompleteBrowserLoginCommand, RefreshMobileTokenCommand, StartBrowserLoginCommand
from src.application.commands.refresh_token_command import LoginCommand
from src.application.dtos.refresh_dtos import BrowserLoginCompleteRequestDto, BrowserLoginStartDto, BrowserLoginStartRequestDto, LoginMethodDto, LoginRequestDto, LoginResponseDto, MobileTokenRefreshRequestDto
from src.application.queries.detect_login_method_query import DetectLoginMethodQuery

router = APIRouter(prefix="/api/authenticate", tags=["Auth"])


@controller(router)
class AuthController:
    mediator: Mediator = Depends(get_mediator)

    @router.post("/login", response_model=LoginResponseDto, dependencies=[Depends(require_service_key)])
    @shared_limiter.limit("5/minute", exempt_when=is_service_caller)
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

    @router.get("/login-method", response_model=LoginMethodDto)
    @shared_limiter.limit("30/minute", exempt_when=is_service_caller)
    async def login_method(self, request: Request, base_url: str = Depends(get_schulnetz_base_url)):
        """Which sign-in the school uses, so a client can show a Microsoft account picker or a credentials form."""
        return await self.mediator.send(DetectLoginMethodQuery(base_url=base_url))

    @router.post("/browser/start", response_model=BrowserLoginStartDto, dependencies=[Depends(require_service_key)])
    @shared_limiter.limit("10/minute", exempt_when=is_service_caller)
    async def browser_start(self, request: Request, body: BrowserLoginStartRequestDto):
        """Start a sign-in the user completes in a browser, for schools detected as `browser`."""
        return await self.mediator.send(StartBrowserLoginCommand(schulnetz_base_url=validate_base_url(body.schulnetz_base_url)))

    @router.post("/browser/complete", response_model=LoginResponseDto, dependencies=[Depends(require_service_key)])
    @shared_limiter.limit("10/minute", exempt_when=is_service_caller)
    async def browser_complete(self, request: Request, body: BrowserLoginCompleteRequestDto):
        """Exchange the `code` from the browser callback for mobile tokens."""
        return await self.mediator.send(CompleteBrowserLoginCommand(schulnetz_base_url=validate_base_url(body.schulnetz_base_url), code=body.code, code_verifier=body.code_verifier, device_id=body.device_id))

    @router.post("/refresh", response_model=LoginResponseDto, dependencies=[Depends(require_service_key)])
    @shared_limiter.limit("10/minute", exempt_when=is_service_caller)
    async def refresh(self, request: Request, body: MobileTokenRefreshRequestDto):
        """Trade a mobile refresh token for new tokens. Fails where the school demands the official app's passkey (`biometric_required`)."""
        return await self.mediator.send(RefreshMobileTokenCommand(schulnetz_base_url=validate_base_url(body.schulnetz_base_url), refresh_token=body.refresh_token, device_id=body.device_id))
