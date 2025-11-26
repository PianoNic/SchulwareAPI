from typing import Optional
from pydantic import BaseModel

class AbsenceNoticeDto(BaseModel):
    id: Optional[str] = None
    studentId: Optional[str] = None
    studentReason: Optional[str] = None
    studentReasonTimestamp: Optional[str] = None
    studentIs18: Optional[bool] = None
    date: Optional[str] = None
    hourFrom: Optional[str] = None
    hourTo: Optional[str] = None
    time: Optional[str] = None
    status: Optional[str] = None
    statusLong: Optional[str] = None
    comment: Optional[str] = None
    isExamLesson: Optional[bool] = None
    profile: Optional[str] = None
    course: Optional[str] = None
    courseId: Optional[str] = None
    absenceId: Optional[str] = None
    absenceSemester: Optional[int] = None
    trainerAcknowledgement: Optional[str] = None
    trainerComment: Optional[str] = None
    trainerCommentTimestamp: Optional[str] = None