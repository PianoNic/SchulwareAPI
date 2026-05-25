"""Composition root for MediatorX.

Registers all command and query handlers and exposes `get_mediator` as a
FastAPI dependency. Controllers obtain the mediator via `Depends(get_mediator)`
and dispatch via `mediator.send(...)`.
"""

from mediatorx import Mediator

from src.application.commands.capture_web_session_command import (
    CaptureWebSessionCommand,
    CaptureWebSessionHandler,
)
from src.application.commands.refresh_token_command import (
    RefreshTokenCommand,
    RefreshTokenHandler,
)
from src.application.queries.get_app_info_query import (
    GetAppInfoQuery,
    GetAppInfoHandler,
)
from src.application.queries.proxy_mobile_rest_query import (
    ProxyMobileRestQuery,
    ProxyMobileRestHandler,
)
from src.application.queries.scrape_agenda_query import (
    ScrapeAgendaQuery,
    ScrapeAgendaHandler,
)
from src.application.queries.scrape_ausweis_query import (
    ScrapeAusweisQuery,
    ScrapeAusweisHandler,
)
from src.application.queries.scrape_listen_query import (
    ScrapeListenQuery,
    ScrapeListenHandler,
)
from src.application.queries.scrape_noten_query import (
    ScrapeNotenQuery,
    ScrapeNotenHandler,
)
from src.application.queries.scrape_unterricht_query import (
    ScrapeUnterrichtQuery,
    ScrapeUnterrichtHandler,
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
    m.register(CaptureWebSessionCommand, CaptureWebSessionHandler)
    m.register(RefreshTokenCommand, RefreshTokenHandler)

    # Queries
    m.register(GetAppInfoQuery, GetAppInfoHandler)
    m.register(ProxyMobileRestQuery, ProxyMobileRestHandler)
    m.register(ScrapeAgendaQuery, ScrapeAgendaHandler)
    m.register(ScrapeAusweisQuery, ScrapeAusweisHandler)
    m.register(ScrapeListenQuery, ScrapeListenHandler)
    m.register(ScrapeNotenQuery, ScrapeNotenHandler)
    m.register(ScrapeUnterrichtQuery, ScrapeUnterrichtHandler)
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
