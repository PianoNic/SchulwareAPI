from pydantic import BaseModel, Field


class AbsenceCreateDto(BaseModel):
    studentId: str = Field(..., description="Student id (from GET /api/mobile/userInfo).")
    dateFrom: str = Field(..., description="First day of the absence, YYYY-MM-DD.")
    dateTo: str = Field(..., description="Last day of the absence, YYYY-MM-DD.")
    hourFrom: str | None = Field(default=None, description="Start time HH:MM (optional).")
    hourTo: str | None = Field(default=None, description="End time HH:MM (optional).")
    reason: str | None = Field(default=None, description="Free-text reason (optional).")
    comment: str | None = Field(default=None, description="Free-text comment (optional).")


class AbsenceCreateResultDto(BaseModel):
    id: str | None = None
    status: str | None = Field(default=None, description='"0" on success, otherwise a Schulnetz error code (e.g. E003).')
    message: str | None = None
