from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import sentry_sdk
from sentry_sdk import set_tag, set_context
from src.infrastructure.monitoring import add_breadcrumb, set_user_context
import time
import traceback
from typing import Callable
import json


class SentryMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enhance Sentry error tracking with request context.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timing the request
        start_time = time.time()

        # Set request context
        set_tag("request.method", request.method)
        set_tag("request.path", request.url.path)
        set_tag("request.host", request.headers.get("host", "unknown"))

        # Add breadcrumb for request
        add_breadcrumb(
            message=f"{request.method} {request.url.path}",
            category="request",
            level="info",
            data={
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "headers": {
                    k: v for k, v in request.headers.items()
                    if k.lower() not in ["authorization", "cookie", "x-api-key"]
                }
            }
        )

        # Extract user information from headers or JWT if available
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                # You might want to decode JWT here to get user info
                # For now, we'll just tag that it's an authenticated request
                set_tag("auth.type", "bearer")
            except Exception:
                pass

        # Set request context for Sentry
        set_context("request", {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query": dict(request.query_params),
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent", "unknown")
        })

        try:
            # Process the request
            response = await call_next(request)

            # Calculate request duration
            duration = time.time() - start_time

            # Add performance breadcrumb
            add_breadcrumb(
                message=f"{request.method} {request.url.path} completed",
                category="request",
                level="info",
                data={
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2)
                }
            )

            # Set performance tags
            set_tag("response.status_code", response.status_code)
            set_tag("response.duration_ms", round(duration * 1000, 2))

            # Track slow requests
            if duration > 5.0:  # More than 5 seconds
                sentry_sdk.capture_message(
                    f"Slow request: {request.method} {request.url.path}",
                    level="warning",
                    extras={
                        "duration": duration,
                        "path": request.url.path,
                        "method": request.method
                    }
                )

            return response

        except HTTPException as exc:
            # Handle HTTP exceptions
            duration = time.time() - start_time

            add_breadcrumb(
                message=f"HTTP exception: {exc.status_code}",
                category="error",
                level="error",
                data={
                    "status_code": exc.status_code,
                    "detail": exc.detail,
                    "duration_ms": round(duration * 1000, 2)
                }
            )

            # Only capture 5xx errors to Sentry
            if exc.status_code >= 500:
                with sentry_sdk.push_scope() as scope:
                    scope.set_context("http_exception", {
                        "status_code": exc.status_code,
                        "detail": exc.detail,
                        "path": request.url.path,
                        "method": request.method
                    })
                    sentry_sdk.capture_exception(exc)

            raise

        except RequestValidationError as exc:
            # Handle validation errors
            duration = time.time() - start_time

            add_breadcrumb(
                message="Request validation error",
                category="validation",
                level="error",
                data={
                    "errors": exc.errors(),
                    "body": exc.body if hasattr(exc, 'body') else None,
                    "duration_ms": round(duration * 1000, 2)
                }
            )

            # Capture validation errors for monitoring
            with sentry_sdk.push_scope() as scope:
                scope.set_context("validation_error", {
                    "errors": exc.errors(),
                    "path": request.url.path,
                    "method": request.method
                })
                scope.level = "warning"
                sentry_sdk.capture_exception(exc)

            raise

        except Exception as exc:
            # Handle unexpected errors
            duration = time.time() - start_time

            add_breadcrumb(
                message=f"Unexpected error: {type(exc).__name__}",
                category="error",
                level="error",
                data={
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "duration_ms": round(duration * 1000, 2),
                    "traceback": traceback.format_exc()
                }
            )

            # Capture all unexpected errors
            with sentry_sdk.push_scope() as scope:
                scope.set_context("unexpected_error", {
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "path": request.url.path,
                    "method": request.method,
                    "duration_ms": round(duration * 1000, 2)
                })
                sentry_sdk.capture_exception(exc)

            raise


class SentryAsyncContextMiddleware:
    """
    ASGI middleware for Sentry context management.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Create a new Sentry scope for this request
            with sentry_sdk.push_scope() as sentry_scope:
                # Set basic request information
                sentry_scope.set_tag("request.type", "http")
                sentry_scope.set_tag("request.path", scope.get("path", "/"))
                sentry_scope.set_tag("request.method", scope.get("method", "UNKNOWN"))

                # Set request context
                sentry_scope.set_context("asgi", {
                    "type": scope.get("type"),
                    "path": scope.get("path"),
                    "method": scope.get("method"),
                    "query_string": scope.get("query_string", b"").decode(),
                    "server": scope.get("server"),
                    "client": scope.get("client"),
                    "scheme": scope.get("scheme")
                })

                await self.app(scope, receive, send)
        else:
            await self.app(scope, receive, send)