from pydantic import BaseModel

class WebUrlsDto(BaseModel):
    start: str
    grades: str
    absent_notices: str
    lesson: str
    agenda: str
    documents: str
    student_id_card: str