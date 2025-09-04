from dataclasses import dataclass, field
from typing import List

from src.application.dtos.web.personal_info_dto import PersonalInfoDto
from src.application.dtos.web.company_info_dto import CompanyInfoDto
from src.application.dtos.mobile.absence_dto import AbsenceDto
from src.application.dtos.mobile.grade_dto import GradeDto
from src.application.dtos.web.event_dto import EventDto
from src.application.dtos.web.holiday_dto import HolidayDto

@dataclass
class SchulnetzDataDto:
    holidays: List[HolidayDto] = field(default_factory=list)
    events: List[EventDto] = field(default_factory=list)
    grades: List[GradeDto] = field(default_factory=list)
    open_absences: List[AbsenceDto] = field(default_factory=list)
    company_info: CompanyInfoDto = field(default_factory=CompanyInfoDto)
    personal_info: PersonalInfoDto = field(default_factory=PersonalInfoDto)