from dataclasses import dataclass

@dataclass
class GradeDto:
    course: str
    topic: str
    date: str
    grade: str