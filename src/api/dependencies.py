"""Composition root for MediatorX.

Registers all command and query handlers and exposes `get_mediator` as a
FastAPI dependency. Controllers obtain the mediator via `Depends(get_mediator)`
and dispatch via `mediator.send(...)`.
"""

from fastapi import Header, HTTPException
from mediatorx import Mediator

from src.application.commands.refresh_token_command import (
    LoginCommand,
    LoginHandler,
)
from src.application.queries.get_app_info_query import (
    GetAppInfoQuery,
    GetAppInfoHandler,
)
from src.application.queries.proxy_mobile_rest_query import (
    ProxyMobileRestQuery,
    ProxyMobileRestHandler,
)
from src.application.queries.scrape_web_page_query import (
    ScrapeWebPageQuery,
    ScrapeWebPageHandler,
)
from src.application.queries.validate_web_session_query import (
    ValidateWebSessionQuery,
    ValidateWebSessionHandler,
)

def build_mediator() -> Mediator:
    m = Mediator()

    # Commands
    m.register(LoginCommand, LoginHandler)

    # Queries
    m.register(GetAppInfoQuery, GetAppInfoHandler)
    m.register(ProxyMobileRestQuery, ProxyMobileRestHandler)
    m.register(ScrapeWebPageQuery, ScrapeWebPageHandler)
    m.register(ValidateWebSessionQuery, ValidateWebSessionHandler)

    # Pipeline behaviors will be added here in the next step
    # m.add_behavior(LoggingBehavior)
    # m.add_behavior(SentryBreadcrumbBehavior)
    # m.add_behavior(PerformanceBehavior)

    return m

_mediator = build_mediator()

def get_mediator() -> Mediator:
    """FastAPI dependency. Returns the process-wide Mediator instance."""
    return _mediator


def get_schulnetz_base_url(
    x_schulnetz_base_url: str | None = Header(
        default=None,
        alias="X-Schulnetz-Base-Url",
        description="Base URL of the target Schulnetz instance, e.g. https://schulnetz.bbbaden.ch",
    ),
) -> str:
    """FastAPI dependency. Returns the per-request Schulnetz base URL from the
    `X-Schulnetz-Base-Url` header. Raises 400 if missing or empty."""
    if not x_schulnetz_base_url:
        raise HTTPException(
            status_code=400,
            detail="Missing required header 'X-Schulnetz-Base-Url'.",
        )
    return x_schulnetz_base_url.rstrip("/")
