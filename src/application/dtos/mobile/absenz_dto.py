from pydantic import BaseModel
from typing import Optional

class AbsenzDto(BaseModel):
    """DTO for Absenzen - absences with a specific reason"""
    id: str
    studentId: str
    dateFrom: str
    dateTo: str
    hourFrom: Optional[str] = None  # Can be null in some cases
    hourTo: Optional[str] = None    # Can be null in some cases
    subject: Optional[str] = None
    subjectId: Optional[str] = None
    profile: str
    profileId: str
    lessons: str
    reason: str  # Required for Absenzen
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
