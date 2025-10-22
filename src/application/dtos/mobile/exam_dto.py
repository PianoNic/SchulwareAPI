from typing import Optional, List
from pydantic import BaseModel

class ExamDto(BaseModel):
    id: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    text: str | None = None
    comment: str | None = None
    roomToken: str | None = None
    roomId: str | None = None
    teachers: list[str] | None = None
    teacherIds: list[str] | None = None
    teacherTokens: list[str] | None = None
    courseId: str | None = None
    courseToken: str | None = None
    courseName: str | None = None
    status: str | None = None
    color: str | None = None
    eventType: str | None = None
    eventRoomStatus: str | None = None
    timetableText: str | None = None
    infoFacilityManagement: str | None = None
    importset: str | None = None
    lessons: list[str] | None = None
    publishToInfoSystem: bool | None = None
    studentNames: list[str] | None = None
    studentIds: list[str] | None = None
    client: str | None = None
    clientname: str | None = None
    weight: str | None = None
