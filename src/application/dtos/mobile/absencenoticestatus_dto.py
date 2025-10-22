from typing import Optional
from pydantic import BaseModel

class AbsenceNoticeStatusDto(BaseModel):
    id: str | None = None
    code: str | None = None
    name: str | None = None
    sort: str | None = None
    comment: str | None = None
    additionalInfo: str | None = None
    iso2: str | None = None
    iso3: str | None = None
