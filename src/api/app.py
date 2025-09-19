from fastapi import FastAPI
from src.application.services.db_service import setup_db
from src.application.services.env_service import load_env
from src.application.services.app_config_service import app_config
from src.api.router_registry import router_registry
from src.infrastructure.logging_config import setup_colored_logging
from src.infrastructure.monitoring import initialize_sentry
from fastapi.openapi.utils import get_openapi
import os
from src.api.middleware.sentry_middleware import SentryMiddleware, SentryAsyncContextMiddleware


setup_colored_logging()

load_env()
setup_db()

# Initialize Sentry/GlitchTip monitoring
initialize_sentry(
    dsn=os.getenv("SENTRY_DSN"),
    environment=app_config.get_environment(),
    release=app_config.get_version(),
    debug=os.getenv("DEBUG", "false").lower() == "true",
    traces_sample_rate=0.1
)

# Get version and environment from application.properties
app_version = app_config.get_version()
app_environment = app_config.get_environment()

app = FastAPI(
    title="Schulware API Wrapper",
    description=f"A FastAPI application to wrap Schulware API endpoints.\n\n**Environment:** {app_environment}",
    version=app_version,
    redoc_url=None,
    docs_url="/"
)

# Add Sentry middleware for enhanced error tracking
app.add_middleware(SentryMiddleware)
app.add_middleware(SentryAsyncContextMiddleware)

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