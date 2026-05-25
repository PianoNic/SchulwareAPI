from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from mediatorx import ICommand, ICommandHandler

from src.api.auth import auth
from src.infrastructure.logging_config import get_logger

logger = get_logger("web_auth")


@dataclass
class AuthenticateWebCommand(ICommand[Any]):
    email: str
    password: str


class AuthenticateWebHandler(ICommandHandler[AuthenticateWebCommand, Any]):
    async def handle(self, command: AuthenticateWebCommand) -> Any:
        email, password = command.email, command.password
        if not email or not password:
            raise HTTPException(status_code=400, detail="Email and password are required for web authentication")

        try:
            logger.info(f"Performing web authentication for user: {email}")
            result = await auth.authenticate_with_credentials(email, password, "web")

            if result["success"]:
                return {
                    "success": True,
                    "message": "Web interface authentication successful",
                    "session_cookies": result["session_cookies"],
                    "navigation_urls": result.get("navigation_urls", {}),
                    "noten_url": result.get("noten_url"),
                    "auth_code": result.get("auth_code"),
                }
            else:
                raise HTTPException(
                    status_code=401,
                    detail=result.get("error", "Web authentication failed"),
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Web authentication error for {email}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Web authentication error: {str(e)}")
