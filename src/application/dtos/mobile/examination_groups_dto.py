from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class ExaminationGroupsDto:
    examGroup: Optional[str]
    weightExamGroup: Optional[str]
    averageExamGroup: Optional[str]