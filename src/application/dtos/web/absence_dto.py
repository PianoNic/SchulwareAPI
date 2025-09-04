from dataclasses import dataclass

@dataclass
class AbsenceDto:
    start: str
    end: str
    excuse_until: str
    status: str