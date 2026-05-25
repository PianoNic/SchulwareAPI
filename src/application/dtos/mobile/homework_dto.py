from pydantic import BaseModel

class HomeworkDto(BaseModel):
    id: str | None = None
    title: str | None = None
    description: str | None = None
    dueDate: str | None = None
    courseId: str | None = None
    courseName: str | None = None
    isCompleted: bool | None = None

class ObjectiveDto(BaseModel):
    id: str | None = None
    title: str | None = None
    description: str | None = None
    date: str | None = None
    courseId: str | None = None
    courseName: str | None = None
