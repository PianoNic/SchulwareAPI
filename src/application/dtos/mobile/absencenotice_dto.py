from typing import Optional
from pydantic import BaseModel

class AbsenceNoticeDto(BaseModel):
    id: str
    studentId: str
    studentReason: Optional[str] = None
    studentReasonTimestamp: Optional[str] = None
    studentIs18: bool
    date: str
    hourFrom: str
    hourTo: str
    time: str
    status: str
    statusLong: str
    comment: Optional[str] = None
    isExamLesson: bool
    profile: str
    course: str
    courseId: str
    absenceId: str
    absenceSemester: int
    trainerAcknowledgement: Optional[str] = None
    trainerComment: Optional[str] = None
    trainerCommentTimestamp: Optional[str] = None