from fastapi import FastAPI
from src.application.services.db_service import setup_db
from src.application.services.env_service import load_env
from src.api.router_registry import router_registry
from src.infrastructure.logging_config import setup_colored_logging
from fastapi.openapi.utils import get_openapi

setup_colored_logging()

load_env()
setup_db()

app = FastAPI(
    title="Schulware API Wrapper",
    description="A FastAPI application to wrap Schulware API endpoints.",
    version="1.0.0",
    redoc_url=None,
    docs_url="/"
)

# TEMPORARY anyOf/oneOf workaround for Dart code generator compatibility
def custom_openapi():
    data = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    if (("components" in data) and ("schemas" in data["components"])
            and ("ValidationError" in data["components"]["schemas"])
            and ("properties" in data["components"]["schemas"]["ValidationError"])
                and ("loc" in data["components"]["schemas"]["ValidationError"]["properties"])
                and ("items" in data["components"]["schemas"]["ValidationError"]["properties"]["loc"])):
        data["components"]["schemas"]["ValidationError"]["properties"]["loc"]["items"] = {"type": "string"}
    return data


router_registry.auto_register(app)

app.openapi = custom_openapi