from dataclasses import dataclass

from mediatorx import ICommand, ICommandHandler

from src.application.dtos.web_session_dtos import WebSessionResponseDto
from src.application.services.env_service import get_env_variable
from src.application.services.web_session_service import capture_web_session


@dataclass
class CaptureWebSessionCommand(ICommand[WebSessionResponseDto]):
    code: str
    state: str | None = None
    code_verifier: str | None = None


class CaptureWebSessionHandler(ICommandHandler[CaptureWebSessionCommand, WebSessionResponseDto]):
    async def handle(self, command: CaptureWebSessionCommand) -> WebSessionResponseDto:
        # `loginto.php` lives on the school's Schulnetz instance (API base),
        # not on the PWA host (`SCHULNETZ_WEB_BASE_URL` points at schulnetz.web.app).
        base_url = get_env_variable("SCHULNETZ_API_BASE_URL")
        cookies, session_info = await capture_web_session(
            base_url, command.code, command.state, command.code_verifier
        )

        if cookies is None:
            return WebSessionResponseDto(
                success=False,
                message="Failed to capture web session. The code may be expired or invalid.",
            )

        return WebSessionResponseDto(
            success=True,
            session_id=cookies.get("PHPSESSID"),
            cookies=cookies,
            session_info=session_info,
            message="Web session captured successfully",
        )
