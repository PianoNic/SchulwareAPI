from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class ExaminationGroupsDto:
    examGroup: Optional[Any]
    weightExamGroup: Optional[Any]
    averageExamGroup: Optional[Any]