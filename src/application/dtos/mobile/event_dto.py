from pydantic import BaseModel
from typing import Optional, List


class EventDto(BaseModel):
    id: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    text: Optional[str] = None
    comment: Optional[str] = None
    roomToken: Optional[str] = None
    roomId: Optional[str] = None
    teachers: Optional[List[str]] = None
    teacherIds: Optional[List[str]] = None
    teacherTokens: Optional[List[str]] = None
    courseId: Optional[str] = None
    courseToken: Optional[str] = None
    courseName: Optional[str] = None
    courseCurriculum: Optional[str] = None
    status: Optional[str] = None
    color: Optional[str] = None
    eventType: Optional[str] = None
    eventRoomStatus: Optional[str] = None
    timetableText: Optional[str] = None
    infoFacilityManagement: Optional[str] = None
    importset: Optional[str] = None
    lessons: Optional[str] = None
    publishToInfoSystem: Optional[str] = None
    studentNames: Optional[str] = None
    studentIds: Optional[str] = None
    client: Optional[str] = None
    clientname: Optional[str] = None
    weight: Optional[float] = None
    absTrackedTimestamp: Optional[str] = None
