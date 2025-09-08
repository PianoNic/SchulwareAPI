from typing import Optional
from pydantic import BaseModel

class AbsenceNoticeStatusDto(BaseModel):
    id: str
    code: str
    name: str
    sort: str
    comment: Optional[str] = None
    additionalInfo: Optional[str] = None
    iso2: Optional[str] = None
    iso3: Optional[str] = None
