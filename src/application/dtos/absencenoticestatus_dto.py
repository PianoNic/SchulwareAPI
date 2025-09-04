from dataclasses import dataclass
from typing import Optional

@dataclass
class AbsenceNoticeStatusDto:
    id: str
    code: str
    name: str
    sort: str
    comment: Optional[str] = None
    additionalInfo: Optional[str] = None
    iso2: Optional[str] = None
    iso3: Optional[str] = None
