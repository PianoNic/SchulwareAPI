from typing import Optional
from pydantic import BaseModel
from datetime import date, time

class LatenessDto(BaseModel):
    id: Optional[str] = None
    dateExcused: Optional[date] = None
    date: Optional[str] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    duration: Optional[str] = None
    reason: Optional[str] = None
    excused: Optional[bool] = None
    extendedDeadline: Optional[int] = None
    courseId: Optional[str] = None
    courseToken: Optional[str] = None
    comment: Optional[str] = None