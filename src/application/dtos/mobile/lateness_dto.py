from pydantic import BaseModel
from datetime import date, time

class LatenessDto(BaseModel):
    id: str | None = None
    dateExcused: date | None = None
    date: str | None = None
    startTime: str | None = None
    endTime: str | None = None
    duration: str | None = None
    reason: str | None = None
    excused: bool | None = None
    extendedDeadline: int | None = None
    courseId: str | None = None
    courseToken: str | None = None
    comment: str | None = None