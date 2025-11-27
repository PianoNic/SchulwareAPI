from typing import Optional
from pydantic import BaseModel
from src.application.dtos.mobile.examination_groups_dto import ExaminationGroupsDto

class GradeDto(BaseModel):
    id: Optional[str] = None
    course: Optional[str] = None
    courseId: Optional[str] = None
    courseType: Optional[str] = None
    examId: Optional[str] = None
    subject: Optional[str] = None
    subjectToken: Optional[str] = None
    title: Optional[str] = None
    date: Optional[str] = None
    mark: Optional[float] = None
    points: Optional[float] = None
    weight: Optional[float] = None
    isConfirmed: Optional[bool] = None
    isConfirmedByTrainer: Optional[bool] = None
    courseGrade: Optional[float] = None
    examinationGroups: Optional[ExaminationGroupsDto] = None
    studentId: Optional[str] = None
    studentName: Optional[str] = None
    inputType: Optional[str] = None
    comment: Optional[str] = None