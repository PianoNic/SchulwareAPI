from dataclasses import dataclass
from typing import Optional, Any
from src.application.dtos.mobile.examination_groups_dto import ExaminationGroupsDto

@dataclass
class GradeDto:
    id: str
    course: str
    courseId: str
    courseType: str
    subject: str
    subjectToken: str
    title: str
    date: str
    mark: str
    points: Optional[str]
    weight: str
    isConfirmed: bool
    courseGrade: str
    examinationGroups: ExaminationGroupsDto
    studentId: Optional[str]
    studentName: Optional[str]
    inputType: str
    comment: Optional[str]