from typing import Optional
from pydantic import BaseModel

class ExaminationGroupsDto(BaseModel):
    examGroup: Optional[str] = None
    weightExamGroup: Optional[str] = None
    averageExamGroup: Optional[str] = None