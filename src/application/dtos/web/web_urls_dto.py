from dataclasses import dataclass

@dataclass
class WebUrlsDto:
    start: str
    grades: str
    absent_notices: str
    lesson: str
    agenda: str
    documents: str
    student_id_card: str