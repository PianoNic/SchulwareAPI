from pydantic import BaseModel
from typing import Optional


class VacationDto(BaseModel):
    id: Optional[str] = None
    dateFrom: Optional[str] = None
    dateTo: Optional[str] = None
    reason: Optional[str] = None
    status: Optional[str] = None
    comment: Optional[str] = None
