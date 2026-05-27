"""DTOs for web session endpoints."""

from pydantic import BaseModel, Field
from typing import Any

class WebSessionRequestDto(BaseModel):
    """Request DTO for capturing a web session from an OAuth code."""
    code: str = Field(..., description="OAuth authorization code from Microsoft SSO")
    state: str = Field(..., description="OAuth state parameter")
    code_verifier: str | None = Field(None, description="PKCE code_verifier from /websession/oauth/url")

class WebSessionResponseDto(BaseModel):
    """Response DTO for web session capture."""
    success: bool = Field(..., description="Whether session capture was successful")
    session_id: str | None = Field(None, description="PHPSESSID value")
    cookies: dict[str, str] | None = Field(None, description="All captured session cookies")
    session_info: dict[str, Any] | None = Field(None, description="Session parameters (id, transid, navigation_urls)")
    message: str | None = Field(None, description="Status message")

class WebScrapeRequestDto(BaseModel):
    """Request DTO for scraping a Schulnetz page."""
    session_id: str = Field(..., description="PHPSESSID cookie value")
    page: str = Field(..., description="Page to scrape: home, grades, absences, agenda, lessons, documents, student_id")
    id: str = Field(..., description="Session id parameter from URL")
    transid: str = Field(..., description="Transaction id parameter from URL")
    user_agent: str | None = Field(None, description="The WebView UA that created the session (Schulnetz binds PHPSESSID to UA)")
    additional_cookies: list[dict[str, str]] | None = Field(
        None,
        description=(
            "Optional extra cookies (typically Microsoft SSO cookies from the "
            "captured context_state) to attach on each request. Required for "
            "Schulnetz instances that perform silent re-SSO through Microsoft "
            "mid-flight (e.g. bs-aarau). Each entry: {name, value, domain}."
        ),
    )

class WebScrapeResponseDto(BaseModel):
    """Response DTO for scraped page."""
    success: bool
    data: Any | None = None
    message: str | None = None
    # Some Schulnetz instances rotate id/transid per-request (one-shot CSRF).
    # When present, callers MUST persist these and use them on the next call.
    refreshed_id: str | None = None
    refreshed_transid: str | None = None


class WebValidateResponseDto(BaseModel):
    """Response DTO for session validation."""
    valid: bool
    message: str
    refreshed_id: str | None = None
    refreshed_transid: str | None = None
