"""DTOs for web session endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class WebSessionRequestDto(BaseModel):
    """Request DTO for capturing a web session from an OAuth code."""
    code: str = Field(..., description="OAuth authorization code from Microsoft SSO")
    state: str = Field(..., description="OAuth state parameter")


class WebSessionResponseDto(BaseModel):
    """Response DTO for web session capture."""
    success: bool = Field(..., description="Whether session capture was successful")
    session_id: Optional[str] = Field(None, description="PHPSESSID value")
    cookies: Optional[Dict[str, str]] = Field(None, description="All captured session cookies")
    session_info: Optional[Dict[str, Any]] = Field(None, description="Session parameters (id, transid, navigation_urls)")
    message: Optional[str] = Field(None, description="Status message")


class WebScrapeRequestDto(BaseModel):
    """Request DTO for scraping a Schulnetz page."""
    session_id: str = Field(..., description="PHPSESSID cookie value")
    page: str = Field(..., description="Page to scrape: home, grades, absences, agenda, lessons, documents, student_id")
    id: str = Field(..., description="Session id parameter from URL")
    transid: str = Field(..., description="Transaction id parameter from URL")


class WebScrapeResponseDto(BaseModel):
    """Response DTO for scraped page."""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
