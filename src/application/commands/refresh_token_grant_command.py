"""⚗️ EXPERIMENTAL (#121) — direct OAuth2 refresh_token grant against /token.php.

Goal of the spike: find out whether Schulnetz issues — and honours — a real
refresh_token when the original authorization flow includes the
`offline_access` scope. If so, every routine token refresh can be a single
HTTP POST instead of a full Playwright/Chromium replay of the captured
browser context.

How to evaluate the results:

    1. Complete a fresh OAuth flow on this branch (the scope now includes
       offline_access). Capture the refresh_token from the /token.php
       response in /api/authenticate/oauth/mobile/callback.
    2. POST to /api/authenticate/refresh-token with
       { schulnetz_base_url, refresh_token }.
    3. Inspect the response:
         - 200 + new access_token  → grant works. Spike succeeds.
                                     Promote endpoint to non-experimental,
                                     make offline_access permanent, document
                                     refresh layering in the README.
         - status_code 400 + error="invalid_grant"
                                   → Schulnetz issued a placeholder token.
                                     Spike fails for this instance. Keep
                                     context_state as the only refresh path.
         - status_code 400 + error="unsupported_grant_type" / 401 / 404
                                   → Server doesn't expose the grant at all.
                                     Close #121 as won't-implement.
    4. Repeat against a second instance once #119 lands (e.g. one of the
       Solothurn schools) — OAuth servers can be configured differently
       per deployment.
"""

from dataclasses import dataclass

import httpx
from mediatorx import ICommand, ICommandHandler

from src.application.commands.refresh_token_command import SCHULNETZ_CLIENT_ID
from src.application.dtos.refresh_dtos import RefreshTokenGrantResponseDto
from src.infrastructure.logging_config import get_logger

logger = get_logger("refresh_token_grant_command")


@dataclass
class RefreshTokenGrantCommand(ICommand[RefreshTokenGrantResponseDto]):
    schulnetz_base_url: str
    refresh_token: str


class RefreshTokenGrantHandler(ICommandHandler[RefreshTokenGrantCommand, RefreshTokenGrantResponseDto]):
    async def handle(self, command: RefreshTokenGrantCommand) -> RefreshTokenGrantResponseDto:
        token_url = f"{command.schulnetz_base_url.rstrip('/')}/token.php"

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": command.refresh_token,
            "client_id": SCHULNETZ_CLIENT_ID,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    token_url,
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        except httpx.RequestError as e:
            logger.error("refresh_token grant network error: %s", e)
            return RefreshTokenGrantResponseDto(
                success=False,
                status_code=0,
                message=f"Network error contacting {token_url}: {e}",
            )

        try:
            body = response.json()
        except ValueError:
            body = {"_non_json_body": response.text[:500]}

        logger.info(
            "Spike #121 refresh_token grant: %s %s -> %d, keys=%s",
            "POST", token_url, response.status_code, sorted(body.keys()) if isinstance(body, dict) else "non-dict",
        )

        ok = response.status_code == 200 and isinstance(body, dict) and "access_token" in body

        return RefreshTokenGrantResponseDto(
            success=ok,
            status_code=response.status_code,
            access_token=body.get("access_token") if isinstance(body, dict) else None,
            refresh_token=body.get("refresh_token") if isinstance(body, dict) else None,
            expires_in=body.get("expires_in") if isinstance(body, dict) else None,
            token_type=body.get("token_type") if isinstance(body, dict) else None,
            scope=body.get("scope") if isinstance(body, dict) else None,
            raw_response=body if isinstance(body, dict) else None,
            message=None if ok else f"Schulnetz rejected the refresh_token grant ({response.status_code}).",
        )
