
from pydantic import BaseModel
from src.application.dtos.mobile.examination_groups_dto import ExaminationGroupsDto

class GradeDto(BaseModel):
    id: str | None = None
    course: str | None = None
    courseId: str | None = None
    courseType: str | None = None
    examId: str | None = None
    subject: str | None = None
    subjectToken: str | None = None
    title: str | None = None
    date: str | None = None
    mark: float | None = None
    points: float | None = None
    weight: float | None = None
    isConfirmed: bool | None = None
    isConfirmedByTrainer: bool | None = None
    courseGrade: float | None = None
    examinationGroups: ExaminationGroupsDto | None = None
    studentId: str | None = None
    studentName: str | None = None
    inputType: str | None = None
    comment: str | None = None