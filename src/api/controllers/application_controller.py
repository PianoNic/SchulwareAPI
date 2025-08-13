import os
from fastapi import APIRouter, logger

log = logger.logger
router = APIRouter()
router_tag = ["Application"]

@router.get("/api/app-info", tags=router_tag)
def app_info():
    environment = os.environ.get('FLASK_ENV', 'unknown environment')
    version = os.environ.get('APP_VERSION', 'unknown version')
    return {"environment": environment, "version": version}

@router.get("/api/health", tags=router_tag)
async def health_check():
    return {"status": "healthy", "service": "SchulwareAPI"}
