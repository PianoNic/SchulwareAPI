"""SSRF guard for caller-supplied Schulnetz base URLs.

Callers pass the target Schulnetz instance per request (header or login body) and
the server then fetches it, so an unvalidated value lets a caller point the server
at internal targets (cloud metadata, loopback, RFC1918). This keeps the proxy to
public http/https hosts only.
"""

import ipaddress
from urllib.parse import urlparse

from fastapi import HTTPException


def is_safe_base_url(url: str) -> bool:
    """True if ``url`` is http/https to a public host - not loopback, link-local,
    cloud-metadata, or a private/reserved address. Public host names are allowed
    (DNS rebinding is out of scope here)."""
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname
    if not host or host.lower() == "localhost":
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_base_url(url: str | None) -> str:
    """Returns the trimmed URL, or raises 400 if it is missing or a disallowed target."""
    trimmed = (url or "").rstrip("/")
    if not is_safe_base_url(trimmed):
        raise HTTPException(status_code=400, detail="Invalid or disallowed Schulnetz base URL.")
    return trimmed
