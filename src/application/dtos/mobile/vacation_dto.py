from pydantic import BaseModel

class VacationDto(BaseModel):
    id: str | None = None
    dateFrom: str | None = None
    dateTo: str | None = None
    reason: str | None = None
    status: str | None = None
    comment: str | None = None
