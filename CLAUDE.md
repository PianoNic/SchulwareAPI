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
  - `SCHULNETZ_API_BASE_URL`: Base URL for the Schulnetz API
  - `SCHULNETZ_WEB_BASE_URL`: Base URL for web scraping
  - `SCHULNETZ_CLIENT_ID`: Client ID for API access
  - `DEBUG_VIDEO_RECORDING`: Enable video recording during authentication (true/false)
  - `DISCORD_WEBHOOK_URL`: Discord webhook URL for error reporting (optional)

### Dependencies
- Install: `pip install -r requirements.txt`
- Install Playwright browsers: `playwright install chromium`

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
├── domain/                    # Domain models
└── infrastructure/            # Database and logging config
```

### Controller Pattern
Controllers use `SchulwareAPIRouter` which auto-generates paths:
- Route decorators: `@router.get("endpoint")` → `/api/{prefix}/{endpoint}`
- Tags generated from filename: `auth_controller.py` → "Auth"
- Rate limiting applied via `slowapi`

### Services Architecture
- **Mobile Service**: `schulnetz_mobile_service.py` - REST API client
- **Web Service**: `schulnetz_web_service.py` - Web scraping with Playwright
- **Token Service**: JWT token management for authentication
- **DB Service**: Peewee ORM with SQLite database

### Authentication Flow
- Unified authentication command supports both mobile and web flows
- JWT tokens issued via `token_service.py`
- Bearer token authentication in API endpoints

## Key Technologies
- **FastAPI**: Web framework with auto-generated OpenAPI docs
- **Playwright**: Web scraping for Schulnetz web interface  
- **Peewee**: Lightweight ORM for SQLite database
- **SlowAPI**: Rate limiting middleware
- **Uvicorn**: ASGI server for production

## Debug & Error Reporting

### Sentry/GlitchTip Integration
- **Error Tracking**: Automatic error capture with Sentry SDK integrated with GlitchTip
- **Performance Monitoring**: Transaction tracking with configurable sampling rates
- **Context Enrichment**: Automatic capture of request context, user information, and breadcrumbs
- **Sensitive Data Filtering**: Automatic filtering of passwords, tokens, and API keys
- **Middleware**: Custom middleware for enhanced error context and slow request detection

### Configuration
- `SENTRY_DSN`: GlitchTip Data Source Name for error reporting
- `ENVIRONMENT`: Current environment (development/staging/production)
- `RELEASE`: Application version for error grouping
- `SENTRY_SAMPLE_RATE`: Error sampling rate (0.0-1.0)
- `SENTRY_TRACES_SAMPLE_RATE`: Performance monitoring sample rate

### Features
- **Authentication Monitoring**: Enhanced error tracking in authentication flows with breadcrumbs
- **Performance Decorators**: `@monitor_performance()` decorator for critical operations
- **Request Tracking**: Automatic capture of request method, path, duration, and status
- **Slow Request Detection**: Alerts for requests taking more than 5 seconds

### Legacy Debug Features
- **Video Recording**: Automatic recording of authentication sessions when `DEBUG_VIDEO_RECORDING=true`
- **Discord Integration**: Error reports with video attachments sent to Discord webhook on authentication failures
- **Trace Files**: Playwright trace files (`.zip`) include screenshots, network logs, and timeline data

## Testing
- Test files located in `src/tests/`
- Run tests with standard pytest commands (no specific test runner configured)

## Database
- SQLite database: `schulware.db`
- Models in `src/domain/` and `src/infrastructure/database.py`
- Auto-setup on application startup via `setup_db()`