"""DTOs for web session endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, Dict


class WebSessionRequestDto(BaseModel):
    """Request DTO for capturing a web session from an OAuth code."""
    code: str = Field(..., description="OAuth authorization code from Microsoft SSO")
    state: str = Field(..., description="OAuth state parameter")


class WebSessionResponseDto(BaseModel):
    """Response DTO for web session capture."""
    success: bool = Field(..., description="Whether session capture was successful")
    session_id: Optional[str] = Field(None, description="PHPSESSID value")
    cookies: Optional[Dict[str, str]] = Field(None, description="All captured session cookies")
    message: Optional[str] = Field(None, description="Status message")


class WebScrapeRequestDto(BaseModel):
    """Request DTO for scraping a Schulnetz page."""
    path: str = Field(default="/index.php", description="Page path to scrape")
    params: Optional[Dict[str, str]] = Field(None, description="Query parameters (pageid, id, transid)")


class WebScrapeResponseDto(BaseModel):
    """Response DTO for scraped page."""
    success: bool
    html: Optional[str] = None
    message: Optional[str] = None
