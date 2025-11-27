from typing import List, Optional
from pydantic import BaseModel

class AgendaDto(BaseModel):
    id: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    text: Optional[str] = None
    comment: Optional[str] = None
    roomToken: Optional[str] = None
    roomId: Optional[str] = None
    teachers: Optional[list[str]] = None
    teacherIds: Optional[list[str]] = None
    teacherTokens: Optional[list[str]] = None
    courseId: Optional[str] = None
    courseToken: Optional[str] = None
    courseName: Optional[str] = None
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
    weight: Optional[str] = None
