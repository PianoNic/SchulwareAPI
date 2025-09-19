import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging
from typing import Optional, Dict, Any
from functools import wraps


def initialize_sentry(
    dsn: Optional[str] = None,
    environment: Optional[str] = None,
    release: Optional[str] = None,
    debug: bool = False,
    sample_rate: float = 1.0,
    traces_sample_rate: float = 0.1
) -> None:
    """
    Initialize Sentry SDK with GlitchTip configuration.

    Args:
        dsn: Sentry DSN (Data Source Name)
        environment: Environment name (development, staging, production)
        release: Release version
        debug: Enable debug mode
        sample_rate: Error sampling rate (0.0 to 1.0)
        traces_sample_rate: Transaction sampling rate for performance monitoring
    """
    dsn = dsn or os.getenv("SENTRY_DSN")

    if not dsn:
        logging.warning("Sentry DSN not configured. Error tracking disabled.")
        return

    environment = environment or os.getenv("ENVIRONMENT", "development")
    release = release or os.getenv("RELEASE", "unknown")

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        debug=debug,
        sample_rate=sample_rate,
        traces_sample_rate=traces_sample_rate,
        integrations=[
            FastApiIntegration(
                transaction_style="endpoint",
                failed_request_status_codes={400, 401, 403, 404, 405, 500, 501, 502, 503, 504}
            ),
            StarletteIntegration(
                transaction_style="endpoint",
                failed_request_status_codes={400, 401, 403, 404, 405, 500, 501, 502, 503, 504}
            ),
            HttpxIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR
            ),
        ],
        before_send=before_send_filter,
        attach_stacktrace=True,
        send_default_pii=False,
        profiles_sample_rate=traces_sample_rate if environment == "production" else 0.0,
    )

    logging.info(f"Sentry initialized for environment: {environment}")


def before_send_filter(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Filter sensitive data before sending to Sentry.

    Args:
        event: The event to be sent to Sentry
        hint: Additional information about the event

    Returns:
        Modified event or None to drop the event
    """
    if "request" in event and event["request"]:
        request = event["request"]

        if "cookies" in request:
            request["cookies"] = "[Filtered]"

        if "headers" in request:
            headers = request["headers"]
            sensitive_headers = ["authorization", "cookie", "x-api-key", "x-auth-token"]
            for header in sensitive_headers:
                if header in headers:
                    headers[header] = "[Filtered]"

        if "data" in request:
            data = request["data"]
            if isinstance(data, dict):
                sensitive_fields = ["password", "token", "secret", "api_key", "auth", "pwd"]
                for field in sensitive_fields:
                    if field in data:
                        data[field] = "[Filtered]"

    if "extra" in event:
        extra = event["extra"]
        sensitive_keys = ["password", "token", "secret", "api_key", "auth", "pwd", "cookie"]
        for key in list(extra.keys()):
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                extra[key] = "[Filtered]"

    return event


def capture_exception(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    level: str = "error",
    fingerprint: Optional[list] = None
) -> Optional[str]:
    """
    Capture an exception with additional context.

    Args:
        error: The exception to capture
        context: Additional context to attach to the error
        level: Error level (debug, info, warning, error, fatal)
        fingerprint: Custom fingerprint for grouping errors

    Returns:
        Event ID if the event was sent, None otherwise
    """
    with sentry_sdk.push_scope() as scope:
        scope.level = level

        if context:
            for key, value in context.items():
                scope.set_context(key, value)

        if fingerprint:
            scope.fingerprint = fingerprint

        return sentry_sdk.capture_exception(error)


def capture_message(
    message: str,
    level: str = "info",
    context: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Capture a message event.

    Args:
        message: The message to capture
        level: Message level
        context: Additional context

    Returns:
        Event ID if the event was sent, None otherwise
    """
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_context(key, value)

        return sentry_sdk.capture_message(message, level=level)


def set_user_context(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    username: Optional[str] = None,
    ip_address: Optional[str] = None,
    **extra_data
) -> None:
    """
    Set user context for error tracking.

    Args:
        user_id: Unique user identifier
        email: User email
        username: Username
        ip_address: IP address
        **extra_data: Additional user data
    """
    user_data = {
        "id": user_id,
        "email": email,
        "username": username,
        "ip_address": ip_address
    }

    user_data = {k: v for k, v in user_data.items() if v is not None}

    if extra_data:
        user_data.update(extra_data)

    sentry_sdk.set_user(user_data if user_data else None)


def set_tag(key: str, value: Any) -> None:
    """Set a tag for all future events."""
    sentry_sdk.set_tag(key, value)


def set_context(name: str, value: Dict[str, Any]) -> None:
    """Set custom context data."""
    sentry_sdk.set_context(name, value)


def add_breadcrumb(
    message: str,
    category: Optional[str] = None,
    level: str = "info",
    data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Add a breadcrumb for debugging.

    Args:
        message: Breadcrumb message
        category: Category for grouping
        level: Breadcrumb level
        data: Additional data
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data
    )


def monitor_performance(operation: str):
    """
    Decorator to monitor function performance.

    Args:
        operation: Name of the operation being monitored
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with sentry_sdk.start_transaction(op=operation, name=func.__name__):
                add_breadcrumb(
                    message=f"Starting {func.__name__}",
                    category=operation,
                    level="info"
                )
                try:
                    result = await func(*args, **kwargs)
                    add_breadcrumb(
                        message=f"Completed {func.__name__}",
                        category=operation,
                        level="info"
                    )
                    return result
                except Exception as e:
                    capture_exception(
                        e,
                        context={
                            "operation": operation,
                            "function": func.__name__,
                            "args": str(args)[:200],
                            "kwargs": str(kwargs)[:200]
                        }
                    )
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with sentry_sdk.start_transaction(op=operation, name=func.__name__):
                add_breadcrumb(
                    message=f"Starting {func.__name__}",
                    category=operation,
                    level="info"
                )
                try:
                    result = func(*args, **kwargs)
                    add_breadcrumb(
                        message=f"Completed {func.__name__}",
                        category=operation,
                        level="info"
                    )
                    return result
                except Exception as e:
                    capture_exception(
                        e,
                        context={
                            "operation": operation,
                            "function": func.__name__,
                            "args": str(args)[:200],
                            "kwargs": str(kwargs)[:200]
                        }
                    )
                    raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


import asyncio