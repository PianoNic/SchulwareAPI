from typing import Optional, List
from pydantic import BaseModel

class ExamDto(BaseModel):
    id: str
    startDate: str
    endDate: str
    text: str
    comment: Optional[str] = None
    roomToken: str
    roomId: Optional[str] = None
    teachers: Optional[List[str]] = None
    teacherIds: Optional[List[str]] = None
    teacherTokens: Optional[List[str]] = None
    courseId: str
    courseToken: str
    courseName: str
    status: Optional[str] = None
    color: str
    eventType: str
    eventRoomStatus: Optional[str] = None
    timetableText: Optional[str] = None
    infoFacilityManagement: Optional[str] = None
    importset: Optional[str] = None
    lessons: Optional[List[str]] = None
    publishToInfoSystem: Optional[bool] = None
    studentNames: Optional[List[str]] = None
    studentIds: Optional[List[str]] = None
    client: str
    clientname: str
    weight: str
