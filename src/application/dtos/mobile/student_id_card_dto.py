from pydantic import BaseModel

class StudentIdCardDto(BaseModel):
    html: str | None = None