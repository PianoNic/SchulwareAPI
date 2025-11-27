from fastapi import Form, Request
from src.application.commands.authenticate_mobile_command import authenticate_mobile_command_async
from src.application.commands.authenticate_web_command import authenticate_web_command_async
from src.api.router_registry import SchulwareAPIRouter, shared_limiter
from src.application.dtos.authenticate_dtos import AuthenticateRequestDto, AuthenticateMobileResponseDto
from src.infrastructure.logging_config import get_logger

router = SchulwareAPIRouter()
logger = get_logger("auth_controller")

@router.post("mobile", response_model=AuthenticateMobileResponseDto)
@shared_limiter.limit("1/30seconds")
async def authenticate_mobile_api(request: Request, email: str = Form(...), password: str = Form(...)):
    return await authenticate_mobile_command_async(email, password)

@router.post("web")
@shared_limiter.limit("1/30seconds")
async def authenticate_web_interface(request: Request, auth_request: AuthenticateRequestDto):
    return await authenticate_web_command_async(auth_request.email, auth_request.password)

@router.get("login")
@shared_limiter.limit("1/second")
async def get_barer_token(request: Request, username:str, password:str):
   return ""