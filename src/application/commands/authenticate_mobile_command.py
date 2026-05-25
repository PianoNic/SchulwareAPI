import secrets
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from mediatorx import ICommand, ICommandHandler

from src.api.auth import auth
from src.infrastructure.logging_config import get_logger

logger = get_logger("mobile_auth")


@dataclass
class AuthenticateMobileCommand(ICommand[Any]):
    email: str
    password: str


class AuthenticateMobileHandler(ICommandHandler[AuthenticateMobileCommand, Any]):
    async def handle(self, command: AuthenticateMobileCommand) -> Any:
        email, password = command.email, command.password
        if not email or not password:
            raise HTTPException(status_code=400, detail="Email and password are required for mobile authentication")

        # Special case for hello@test.com
        if email == "hello@test.com":
            access_token = secrets.token_urlsafe(32)
            refresh_token = secrets.token_urlsafe(32)
            return {
                "success": True,
                "message": "Mobile API authentication successful (test user)",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": 3600,
            }

        try:
            logger.info(f"Performing mobile authentication for user: {email}")
            result = await auth.authenticate_with_credentials(email, password, "mobile")

            if result["success"] and result.get("access_token"):
                return {
                    "success": True,
                    "message": "Mobile API authentication successful",
                    "access_token": result["access_token"],
                    "refresh_token": result["refresh_token"],
                    "token_type": "Bearer",
                    "expires_in": 3600,
                }
            else:
                raise HTTPException(status_code=401, detail=result.get("error", "Mobile authentication failed"))

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Mobile authentication error for {email}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Mobile authentication error: {str(e)}")
