from pydantic import BaseModel
from typing import Optional
from datetime import date, time

class LatenessDto(BaseModel):
    id: str
    date: date
    startTime: time
    endTime: time
    duration: str
    reason: Optional[str]
    excused: bool
    dateExcused: Optional[date]
    extendedDeadline: int
    courseId: str
    courseToken: str
    comment: Optional[str]