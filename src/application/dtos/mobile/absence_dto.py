from pydantic import BaseModel
from typing import Optional

class AbsenceDto(BaseModel):
    id: str | None = None
    studentId: str | None = None
    dateFrom: str | None = None
    dateTo: str | None = None
    hourFrom: str | None = None
    hourTo: str | None = None
    subject: str | None = None
    subjectId: str | None = None
    profile: str | None = None
    profileId: str | None = None
    lessons: str | None = None
    reason: str | None = None
    category: str | None = None
    comment: str | None = None
    remark: str | None = None
    isAcknowledged: bool | None = None
    isExcused: bool | None = None
    excusedDate: str | None = None
    additionalPeriod: int | None = None
    statusEAE: str | None = None
    dateEAE: str | None = None
    statusEAB: str | None = None
    dateEAB: str | None = None
    commentEAB: str | None = None
    studentTimestamp: str | None = None