from dataclasses import dataclass

from mediatorx import ICommand, ICommandHandler

from src.application.dtos.web_session_dtos import WebSessionResponseDto
from src.application.services.env_service import get_env_variable
from src.application.services.web_session_service import capture_web_session

@dataclass
class CaptureWebSessionCommand(ICommand[WebSessionResponseDto]):
    code: str
    state: str | None = None

class CaptureWebSessionHandler(ICommandHandler[CaptureWebSessionCommand, WebSessionResponseDto]):
    async def handle(self, command: CaptureWebSessionCommand) -> WebSessionResponseDto:
        return await capture_web_session_command_async(command.code, command.state)

async def capture_web_session_command_async(code: str, state: str | None) -> WebSessionResponseDto:
    base_url = get_env_variable("SCHULNETZ_WEB_BASE_URL")
    cookies, session_info = await capture_web_session(base_url, code, state)

    if cookies is None:
        return WebSessionResponseDto(
            success=False,
            message="Failed to capture web session. The code may be expired or invalid."
        )

    return WebSessionResponseDto(
        success=True,
        session_id=cookies.get("PHPSESSID"),
        cookies=cookies,
        session_info=session_info,
        message="Web session captured successfully"
    )
