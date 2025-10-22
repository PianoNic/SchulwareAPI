from typing import Optional
from pydantic import BaseModel
from src.application.dtos.mobile.examination_groups_dto import ExaminationGroupsDto

class GradeDto(BaseModel):
    id: str | None = None
    course: str | None = None
    courseId: str | None = None
    courseType: str | None = None
    subject: str | None = None
    subjectToken: str | None = None
    title: str | None = None
    date: str | None = None
    mark: str | None = None
    points: str | None = None
    weight: str | None = None
    isConfirmed: bool | None = None
    courseGrade: str | None = None
    examinationGroups: ExaminationGroupsDto | None = None
    studentId: str | None = None
    studentName: str | None = None
    inputType: str | None = None
    comment: str | None = None