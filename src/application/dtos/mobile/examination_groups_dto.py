from typing import Optional
from pydantic import BaseModel

class ExaminationGroupsDto(BaseModel):
    examGroup: str | None = None
    weightExamGroup: str | None = None
    averageExamGroup: str | None = None