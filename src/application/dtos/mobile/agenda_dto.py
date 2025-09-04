from dataclasses import dataclass
from typing import List, Optional

@dataclass
class AgendaDto:
    id: str
    startDate: str
    endDate: str
    text: str
    comment: str
    roomToken: str
    roomId: str
    teachers: List[str]
    teacherIds: List[str]
    teacherTokens: List[str]
    courseId: str
    courseToken: str
    courseName: str
    status: str
    color: str
    eventType: str
    eventRoomStatus: Optional[str] = None
    timetableText: Optional[str] = None
    infoFacilityManagement: Optional[str] = None
    importset: Optional[str] = None
    lessons: Optional[str] = None
    publishToInfoSystem: Optional[str] = None
    studentNames: Optional[str] = None
    studentIds: Optional[str] = None
    client: str = ""
    clientname: str = ""
    weight: Optional[str] = None
