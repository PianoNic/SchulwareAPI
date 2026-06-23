"""DTOs for web session endpoints."""

from pydantic import BaseModel, Field

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

class WebScrapeRequestDto(BaseModel):
    """Request DTO for scraping a Schulnetz page."""
    session_id: str = Field(..., description="PHPSESSID cookie value")
    page: str = Field(..., description="Page to scrape: home, grades, absences, agenda, lessons, documents, student_id")
    id: str = Field(..., description="Session id parameter from URL")
    transid: str = Field(..., description="Transaction id parameter from URL")
    user_agent: str | None = Field(None, description="The WebView UA that created the session (Schulnetz binds PHPSESSID to UA)")

class WebDownloadRequestDto(BaseModel):
    """Request DTO for downloading a filestore document's raw bytes."""
    session_id: str = Field(..., description="PHPSESSID cookie value")
    download_url: str = Field(..., description="Relative export link from the documents scrape (index.php?pageid=10051&...)")
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
