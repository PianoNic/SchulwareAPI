from typing import Optional
from pydantic import BaseModel

class AbsenceNoticeDto(BaseModel):
    id: str | None = None
    studentId: str | None = None
    studentReason: str | None = None
    studentReasonTimestamp: str | None = None
    studentIs18: bool | None = None
    date: str | None = None
    hourFrom: str | None = None
    hourTo: str | None = None
    time: str | None = None
    status: str | None = None
    statusLong: str | None = None
    comment: str | None = None
    isExamLesson: bool | None = None
    profile: str | None = None
    course: str | None = None
    courseId: str | None = None
    absenceId: str | None = None
    absenceSemester: int | None = None
    trainerAcknowledgement: str | None = None
    trainerComment: str | None = None
    trainerCommentTimestamp: str | None = None