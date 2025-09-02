from fastapi import FastAPI, Depends
from fastapi.security import HTTPBearer
from src.application.dtos.auth_dto import MobileSessionDto, WebSessionDto
from src.application.services.db_service import create_or_update_user, setup_db
from src.application.services.env_service import load_env
from src.api.router_registry import router_registry
from src.infrastructure.logging_config import setup_colored_logging
setup_colored_logging()

load_env()
setup_db()

mobile_dto_1 = MobileSessionDto(
    access_token="token_user1_a",
    refresh_token="token_user1_r",
    expires_in=3600
)

web_dto_1 = WebSessionDto(php_session_id="session_id_user1")

create_or_update_user(user_email="hello@gmail.com", mobile_session_dto=mobile_dto_1, web_session_dto=web_dto_1)

app = FastAPI(
    title="Schulnetz API Wrapper",
    description="A FastAPI application to wrap Schulnetz API endpoints.",
    version="1.0.0",
    redoc_url=None,
    docs_url="/"
)

mobile_dto_3 = MobileSessionDto(
    access_token="token_user1_ass",
    refresh_token="token_user1_rss",
    expires_in=36003
)

web_dto_3 = WebSessionDto(php_session_id="session_id_user133")

create_or_update_user(user_email="hello@gmail.com", mobile_session_dto=mobile_dto_3, web_session_dto=web_dto_3)

router_registry.auto_register(app)