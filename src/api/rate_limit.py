"""Shared rate-limit infrastructure.

Provides the process-wide `shared_limiter` instance plus a reverse-proxy-aware
client IP resolver and the standard 429 response handler.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

def get_client_ip(request: Request) -> str:
    """Resolve the real client IP, honoring X-Forwarded-For / X-Real-IP."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    return get_remote_address(request)

shared_limiter = Limiter(key_func=get_client_ip)

def shared_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
