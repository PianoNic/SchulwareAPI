from pydantic import BaseModel
from typing import Optional


class HomeworkDto(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    dueDate: Optional[str] = None
    courseId: Optional[str] = None
    courseName: Optional[str] = None
    isCompleted: Optional[bool] = None


class ObjectiveDto(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    courseId: Optional[str] = None
    courseName: Optional[str] = None
