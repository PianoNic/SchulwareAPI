from typing import Optional
from pydantic import BaseModel

class AbsenceNoticeStatusDto(BaseModel):
    id: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    sort: Optional[str] = None
    comment: Optional[str] = None
    additionalInfo: Optional[str] = None
    iso2: Optional[str] = None
    iso3: Optional[str] = None
