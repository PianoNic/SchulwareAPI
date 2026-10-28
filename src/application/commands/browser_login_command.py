"""Sign-in in a browser, for schools whose login can't be filled in headlessly (e.g. a cantonal login).

The client opens the authorize URL, the user signs in however the school asks, and the browser lands
on the Schulnetz app callback with a `code`. Exchanging it gives mobile tokens bound to `device_id`.
"""

import uuid
from dataclasses import dataclass

from mediatorx import ICommand, ICommandHandler

from src.api.auth.auth import exchange_code_for_tokens, generate_oauth_url, refresh_mobile_tokens
from src.application.dtos.refresh_dtos import BrowserLoginStartDto, LoginResponseDto

CALLBACK_URL = "https://schulnetz.web.app/callback"


@dataclass
class StartBrowserLoginCommand(ICommand[BrowserLoginStartDto]):
    schulnetz_base_url: str


class StartBrowserLoginHandler(ICommandHandler[StartBrowserLoginCommand, BrowserLoginStartDto]):
    async def handle(self, command: StartBrowserLoginCommand) -> BrowserLoginStartDto:
        auth = generate_oauth_url(command.schulnetz_base_url.rstrip("/"), auth_type="mobile")
        return BrowserLoginStartDto(auth_url=auth["auth_url"], callback_url=CALLBACK_URL, state=auth["state"], code_verifier=auth["code_verifier"], device_id=str(uuid.uuid4()))


@dataclass
class CompleteBrowserLoginCommand(ICommand[LoginResponseDto]):
    schulnetz_base_url: str
    code: str
    code_verifier: str
    device_id: str


class CompleteBrowserLoginHandler(ICommandHandler[CompleteBrowserLoginCommand, LoginResponseDto]):
    async def handle(self, command: CompleteBrowserLoginCommand) -> LoginResponseDto:
        access_token, refresh_token = await exchange_code_for_tokens(command.code, command.code_verifier, command.schulnetz_base_url.rstrip("/"), command.device_id)
        if not access_token:
            return LoginResponseDto(success=False, message="Schulnetz refused the sign-in code")
        return LoginResponseDto(success=True, access_token=access_token, refresh_token=refresh_token, message="Signed in through the browser")


@dataclass
class RefreshMobileTokenCommand(ICommand[LoginResponseDto]):
    schulnetz_base_url: str
    refresh_token: str
    device_id: str


class RefreshMobileTokenHandler(ICommandHandler[RefreshMobileTokenCommand, LoginResponseDto]):
    async def handle(self, command: RefreshMobileTokenCommand) -> LoginResponseDto:
        access_token, refresh_token, error = await refresh_mobile_tokens(command.refresh_token, command.device_id, command.schulnetz_base_url.rstrip("/"))
        if not access_token:
            return LoginResponseDto(success=False, message=f"Refresh refused: {error}")
        return LoginResponseDto(success=True, access_token=access_token, refresh_token=refresh_token, message="Mobile tokens refreshed")
