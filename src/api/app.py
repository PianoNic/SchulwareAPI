from fastapi import FastAPI, Depends
from fastapi.security import HTTPBearer
from src.api.router_registry import router_registry


app = FastAPI(
    title="Schulnetz API Wrapper",
    description="A FastAPI application to wrap Schulnetz API endpoints.",
    version="1.0.0",
    redoc_url=None,
    docs_url="/"
)

router_registry.auto_register(app)