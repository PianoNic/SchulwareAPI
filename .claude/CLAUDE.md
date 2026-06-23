# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
SchulwareAPI is a unified FastAPI application that provides access to Schulnetz systems through both mobile REST endpoints and web scraping. It includes interactive Swagger UI documentation and supports Docker deployment.

## Development Commands

### Running the Application
- **Local development**: `python asgi.py` (runs on http://localhost:8000)
- **Docker development**: `docker compose up -d`
- **Docker build**: `docker build -t schulware-api .`

### Environment Setup
- Copy `.env.example` to `.env` and configure:
  - `SCHULNETZ_WEB_BASE_URL`: Base URL for web scraping (PWA host)
  - `SCHULNETZ_CLIENT_ID`: Client ID for API access
  - `SENTRY_DSN`: (Optional) GlitchTip Data Source Name for error reporting
- The per-school API base URL is **not** configured here. Clients pass it
  per-request via the `X-Schulnetz-Base-Url` header (or the `schulnetz_base_url`
  body field on `/api/authenticate/login`).

### Dependencies
- Install: `pip install -r requirements.txt`
- No browser needed: Microsoft Entra OAuth login is headless via the `ms-entrance` package (`entrance.login`).

## Architecture

### Core Components
- **FastAPI Application**: `src/api/app.py` - Main application setup with custom OpenAPI schema
- **Router Registry**: `src/api/router_registry.py` - Auto-discovery and registration of controllers
- **Custom Router**: `SchulwareAPIRouter` class with automatic path generation `/api/{prefix}/{endpoint}`

### Directory Structure
```
src/
├── api/
│   ├── app.py                 # Main FastAPI application
│   ├── router_registry.py     # Auto-registration system
│   ├── controllers/           # API endpoint controllers
│   └── auth/                  # Authentication components
├── application/
│   ├── commands/              # Command handlers
│   ├── dtos/                  # Data transfer objects
│   ├── queries/               # Query handlers
│   └── services/              # Business logic services
└── infrastructure/            # Logging and monitoring config
```

### Controller Pattern
Controllers use `SchulwareAPIRouter` which auto-generates paths:
- Route decorators: `@router.get("endpoint")` → `/api/{prefix}/{endpoint}`
- Tags generated from filename: `auth_controller.py` → "Auth"
- Rate limiting applied via `slowapi`

### Application Layer (CQRS via MediatorX)
- **Commands**: `src/application/commands/` — state-changing operations (e.g. `CaptureWebSessionCommand`, `RefreshTokenCommand`)
- **Queries**: `src/application/queries/` — read operations (e.g. `ProxyMobileRestQuery`, `ScrapeWebPageQuery`)
- Each command/query is a dataclass paired with a handler; dispatched via `mediator.send(...)` from controllers
- Handler registration is centralized in `src/api/dependencies.py`

### Authentication Flow
- Stateless: the caller owns persistence of the returned `session_cookies` jar
- **One endpoint** — `POST /api/authenticate/login`. Pass `email` + `password`
  (+ `totp_secret`/`totp_code`) for a credential login, and/or `session_cookies`
  from a previous response for a silent passwordless re-auth. Returns mobile
  tokens, the web session (PHPSESSID + id/transid), and rotated `session_cookies`.
- Bearer token authentication on mobile-proxy endpoints

## Key Technologies
- **FastAPI**: Web framework with auto-generated OpenAPI docs
- **MediatorX**: CQRS mediator for command/query dispatch
- **ms-entrance**: browserless Microsoft Entra OAuth login (`entrance.login`) — replaces Playwright. Web scraping is plain `httpx`.
- **SlowAPI**: Rate limiting middleware
- **Uvicorn**: ASGI server for production

## Error Reporting

### Sentry/GlitchTip Integration
- **Error Tracking**: Automatic error capture with Sentry SDK integrated with GlitchTip
- **Performance Monitoring**: Transaction tracking with configurable sampling rates
- **Context Enrichment**: Automatic capture of request context, user information, and breadcrumbs
- **Sensitive Data Filtering**: Automatic filtering of passwords, tokens, and API keys
- **Middleware**: Custom middleware for enhanced error context and slow request detection

### Configuration
- `SENTRY_DSN`: GlitchTip Data Source Name for error reporting

### Features
- **Authentication Monitoring**: Enhanced error tracking in authentication flows with breadcrumbs
- **Performance Decorators**: `@monitor_performance()` decorator for critical operations
- **Request Tracking**: Automatic capture of request method, path, duration, and status
- **Slow Request Detection**: Alerts for requests taking more than 5 seconds

## State
SchulwareAPI is **stateless** — there is no database. Per-user data (OAuth tokens,
session_cookies, web session params) is held by the calling client and
passed back in on each request.