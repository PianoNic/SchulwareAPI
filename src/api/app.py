from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from src.application.services.db_service import setup_db
from src.application.services.env_service import load_env
from src.api.router_registry import router_registry
from src.infrastructure.logging_config import setup_colored_logging

setup_colored_logging()

load_env()
setup_db()

app = FastAPI(
    title="Schulnetz API Wrapper",
    description="A FastAPI application to wrap Schulnetz API endpoints.",
    version="1.0.0",
    redoc_url=None,
    docs_url="/"
)

router_registry.auto_register(app)