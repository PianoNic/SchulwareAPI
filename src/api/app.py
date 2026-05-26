import os

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from slowapi.errors import RateLimitExceeded

from src.api.controllers import (
    app_controller,
    auth_controller,
    mobile_proxy_controller,
    web_api_controller,
    web_session_controller,
)
from src.api.middleware.sentry_middleware import SentryMiddleware, SentryAsyncContextMiddleware
from src.api.rate_limit import shared_limiter, shared_rate_limit_exceeded_handler
from src.application.services.app_config_service import app_config
from src.application.services.env_service import load_env
from src.infrastructure.logging_config import setup_colored_logging
from src.infrastructure.monitoring import initialize_sentry

setup_colored_logging()

load_env()

# Initialize Sentry/GlitchTip monitoring
initialize_sentry(
    dsn=os.getenv("SENTRY_DSN"),
    environment=app_config.get_environment(),
    release=app_config.get_version(),
    debug=app_config.is_debug(),
    traces_sample_rate=0.1
)

def _custom_operation_id(route: APIRoute) -> str:
    """Generate operationIds as kebab-joined path segments after `/api/`.

    Example: `/api/app/app-info` -> `app-app-info`.
    """
    parts = route.path.strip("/").split("/")
    if parts and parts[0] == "api":
        parts = parts[1:]
    return "-".join(parts) if parts else "root"

_API_DESCRIPTION = f"""
Wraps Schulnetz to provide a unified and easy-to-use REST API.

## Per-Request Schulnetz Instance

Every Schulnetz-backed endpoint (mobile proxy, web session, OAuth URL/callback)
requires the school's base URL on each request via the **`X-Schulnetz-Base-Url`**
HTTP header:

```
X-Schulnetz-Base-Url: https://schulnetz.bbbaden.ch
```

Requests without this header return `400 Bad Request`. This lets a single
SchulwareAPI deployment serve any Schulnetz school instance — the caller
decides per request.

The only exception is `POST /api/authenticate/refresh`, which carries the base
URL as a `schulnetz_base_url` field in its JSON body instead.

**Environment:** {app_config.get_environment()}
""".strip()

app = FastAPI(
    title="SchulwareAPI",
    description=_API_DESCRIPTION,
    version=app_config.get_version(),
    redoc_url=None,
    docs_url="/",
    generate_unique_id_function=_custom_operation_id,
)

# Sentry middleware for enhanced error tracking
app.add_middleware(SentryMiddleware)
app.add_middleware(SentryAsyncContextMiddleware)

# Rate limiting
app.state.limiter = shared_limiter
app.add_exception_handler(RateLimitExceeded, shared_rate_limit_exceeded_handler)

# Routers
app.include_router(app_controller.router)
app.include_router(auth_controller.router)
app.include_router(mobile_proxy_controller.router)
app.include_router(web_api_controller.router)
app.include_router(web_session_controller.router)

def _flatten_any_of_nullable(obj):
    if isinstance(obj, dict):
        if "anyOf" in obj and isinstance(obj["anyOf"], list) and len(obj["anyOf"]) == 2:
            types = obj["anyOf"]
            null_type = next((t for t in types if t.get("type") == "null"), None)
            real_type = next((t for t in types if t.get("type") != "null"), None)
            if null_type and real_type:
                obj.pop("anyOf")
                if "$ref" in real_type:
                    obj["$ref"] = real_type["$ref"]
                    obj["nullable"] = True
                elif "type" in real_type:
                    obj["type"] = real_type["type"]
                    obj["nullable"] = True
                    for k, v in real_type.items():
                        if k != "type":
                            obj[k] = v
                return obj
        for v in obj.values():
            _flatten_any_of_nullable(v)
    elif isinstance(obj, list):
        for item in obj:
            _flatten_any_of_nullable(item)
    return obj

def custom_openapi():
    data = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    _flatten_any_of_nullable(data)
    if (("components" in data) and ("schemas" in data["components"])
            and ("ValidationError" in data["components"]["schemas"])
            and ("properties" in data["components"]["schemas"]["ValidationError"])
                and ("loc" in data["components"]["schemas"]["ValidationError"]["properties"])
                and ("items" in data["components"]["schemas"]["ValidationError"]["properties"]["loc"])):
        data["components"]["schemas"]["ValidationError"]["properties"]["loc"]["items"] = {"type": "string"}
    return data

app.openapi = custom_openapi
