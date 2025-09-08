from typing import Optional
from pydantic import BaseModel
from src.application.dtos.mobile.examination_groups_dto import ExaminationGroupsDto

class GradeDto(BaseModel):
    id: str
    course: str
    courseId: str
    courseType: str
    subject: str
    subjectToken: str
    title: str
    date: str
    mark: str
    points: Optional[str] = None
    weight: str
    isConfirmed: bool
    courseGrade: str
    examinationGroups: ExaminationGroupsDto
    studentId: Optional[str] = None
    studentName: Optional[str] = None
    inputType: str
    comment: Optional[str] = None