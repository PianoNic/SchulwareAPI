"""Shared rate-limit infrastructure.

Provides the process-wide `shared_limiter` instance, a reverse-proxy-aware
client IP resolver, the service-key check for the Schuly backend, and the
standard 429 response handler.
"""

import hashlib
import hmac
import ipaddress
import os
from contextvars import ContextVar

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from limits import parse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

SERVICE_KEY_HEADER = "X-Service-Key"

_service_caller: ContextVar[bool] = ContextVar("service_caller", default=False)
_per_token_limit = parse("60/minute")


def _trusted_proxies() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    raw = os.getenv("TRUSTED_PROXIES") or ""
    return [ipaddress.ip_network(cidr.strip(), strict=False) for cidr in raw.split(",") if cidr.strip()]


def _is_trusted_proxy(host: str) -> bool:
    """A configured TRUSTED_PROXIES entry, or by default any private/loopback peer."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    proxies = _trusted_proxies()
    if proxies:
        return any(address in network for network in proxies)
    return address.is_private or address.is_loopback


def get_client_ip(request: Request) -> str:
    """Resolve the real client IP; X-Forwarded-For / X-Real-IP only count when set by a trusted proxy."""
    peer = get_remote_address(request)
    if not _is_trusted_proxy(peer):
        return peer

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    return peer


def is_service_request(request: Request) -> bool:
    """True when the request carries the configured SERVICE_API_KEY (the Schuly backend)."""
    expected = os.getenv("SERVICE_API_KEY")
    provided = request.headers.get(SERVICE_KEY_HEADER)
    return bool(expected and provided and hmac.compare_digest(provided, expected))


def is_service_caller() -> bool:
    """`exempt_when` for per-IP limits: all backend traffic shares one IP, so it must not share one bucket."""
    return _service_caller.get()


class ServiceCallerMiddleware:
    """Marks the current request as a service call before any limit is evaluated."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            _service_caller.set(is_service_request(Request(scope)))
        await self.app(scope, receive, send)


def require_service_key(request: Request) -> None:
    """Open while SERVICE_API_KEY is unset; once set, only callers presenting it get through."""
    if os.getenv("SERVICE_API_KEY") and not is_service_request(request):
        raise HTTPException(status_code=401, detail="Invalid service key.")


def limit_per_token(request: Request) -> None:
    """One bucket per Schulnetz bearer token, so the limit scales with the number of users."""
    authorization = request.headers.get("Authorization")
    key = hashlib.sha256(authorization.encode()).hexdigest() if authorization else get_client_ip(request)
    if not shared_limiter.limiter.hit(_per_token_limit, "mobile", key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


shared_limiter = Limiter(key_func=get_client_ip)

def shared_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
