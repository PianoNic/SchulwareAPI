from typing import Optional
from pydantic import BaseModel

class StudentIdCardDto(BaseModel):
    html: Optional[str] = None