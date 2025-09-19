from pydantic import BaseModel
from typing import Optional

class AbsenceDto(BaseModel):
    id: str
    studentId: str
    dateFrom: str
    dateTo: str
    hourFrom: Optional[str] = None
    hourTo: Optional[str] = None
    subject: Optional[str] = None
    subjectId: Optional[str] = None
    profile: str
    profileId: str
    lessons: str
    reason: str
    category: str
    comment: str
    remark: Optional[str] = None
    isAcknowledged: bool
    isExcused: bool
    excusedDate: Optional[str] = None
    additionalPeriod: int
    statusEAE: str
    dateEAE: Optional[str] = None
    statusEAB: str
    dateEAB: Optional[str] = None
    commentEAB: Optional[str] = None
    studentTimestamp: Optional[str] = None