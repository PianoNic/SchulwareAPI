from dataclasses import dataclass
from typing import Optional, List

@dataclass
class ExamDto:
    id: str
    startDate: str
    endDate: str
    text: str
    comment: Optional[str]
    roomToken: str
    roomId: Optional[str]
    teachers: Optional[List[str]]
    teacherIds: Optional[List[str]]
    teacherTokens: Optional[List[str]]
    courseId: str
    courseToken: str
    courseName: str
    status: Optional[str]
    color: str
    eventType: str
    eventRoomStatus: Optional[str]
    timetableText: Optional[str]
    infoFacilityManagement: Optional[str]
    importset: Optional[str]
    lessons: Optional[List[str]]
    publishToInfoSystem: Optional[bool]
    studentNames: Optional[List[str]]
    studentIds: Optional[List[str]]
    client: str
    clientname: str
    weight: str
