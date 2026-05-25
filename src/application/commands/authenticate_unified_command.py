from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from mediatorx import ICommand, ICommandHandler

from src.api.auth import auth
from src.infrastructure.logging_config import get_logger
from src.infrastructure.monitoring import (
    add_breadcrumb,
    capture_exception,
    monitor_performance,
    set_context,
    set_user_context,
)

logger = get_logger("unified_auth")


@dataclass
class AuthenticateUnifiedCommand(ICommand[Any]):
    email: str
    password: str


class AuthenticateUnifiedHandler(ICommandHandler[AuthenticateUnifiedCommand, Any]):
    @monitor_performance("authentication.unified")
    async def handle(self, command: AuthenticateUnifiedCommand) -> Any:
        email, password = command.email, command.password
        if not email or not password:
            raise HTTPException(status_code=400, detail="Email and password are required")

        set_user_context(email=email)
        add_breadcrumb(
            message=f"Starting unified authentication for user: {email}",
            category="auth",
            level="info",
        )

        try:
            logger.info(f"Performing unified authentication for user: {email}")

            add_breadcrumb(
                message="Attempting navigation listener approach",
                category="auth",
                level="info",
            )
            result = await auth.authenticate_unified(email, password)

            if not result["success"]:
                logger.info("Navigation listener approach failed, trying response listener...")
                add_breadcrumb(
                    message="Navigation listener failed, trying response listener",
                    category="auth",
                    level="warning",
                )
                result = await auth.authenticate_unified_webapp_flow(email, password)

            if result["success"]:
                add_breadcrumb(
                    message="Authentication successful",
                    category="auth",
                    level="info",
                )

                set_context("auth_result", {
                    "success": True,
                    "method": "unified",
                    "user": email,
                })

                return {
                    "success": True,
                    "message": "Unified authentication successful",
                    "mobile": {
                        "access_token": result["access_token"],
                        "refresh_token": result["refresh_token"],
                        "token_type": "Bearer",
                        "expires_in": 3600,
                    },
                    "web": {
                        "session_cookies": result["session_cookies"],
                        "navigation_urls": result["navigation_urls"],
                        "noten_url": result["noten_url"],
                        "auth_code": result["auth_code"],
                    },
                }
            else:
                error_detail = result.get("error", "Unified authentication failed")
                add_breadcrumb(
                    message=f"Authentication failed: {error_detail}",
                    category="auth",
                    level="error",
                    data={"error": error_detail},
                )
                raise HTTPException(status_code=401, detail=error_detail)

        except HTTPException as he:
            capture_exception(
                he,
                context={
                    "auth_type": "unified",
                    "user": email,
                    "status_code": he.status_code,
                },
                level="warning",
            )
            raise
        except Exception as e:
            logger.error(f"Unified authentication error for {email}: {str(e)}")
            capture_exception(
                e,
                context={
                    "auth_type": "unified",
                    "user": email,
                    "error_type": type(e).__name__,
                },
                level="error",
            )
            raise HTTPException(status_code=500, detail=f"Unified authentication error: {str(e)}")
