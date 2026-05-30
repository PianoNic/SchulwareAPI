"""DTOs for web session endpoints."""

from pydantic import BaseModel, Field
from typing import Any

from src.application.dtos.web.scrape_dtos import (
    AbsencesPageDto,
    AgendaPageDto,
    DocumentsPageDto,
    GradesPageDto,
    HomePageDto,
    LessonsPageDto,
    ScheduleEventDto,
    WebStudentIdCardDto,
)

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

class WebScrapeResponseDto(BaseModel):
    """Typed response for a scraped Schulnetz page.

    Exactly one of the page fields is populated, matching the requested `page`.
    """
    success: bool
    message: str | None = None
    home: HomePageDto | None = None
    grades: GradesPageDto | None = None
    absences: AbsencesPageDto | None = None
    lessons: LessonsPageDto | None = None
    agenda: AgendaPageDto | None = None
    schedule: list[ScheduleEventDto] | None = None
    documents: DocumentsPageDto | None = None
    student_id: WebStudentIdCardDto | None = None
