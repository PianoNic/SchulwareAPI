from typing import Optional
from pydantic import BaseModel

class ClassInfoDto(BaseModel):
    id: Optional[str] = None
    token: Optional[str] = None
    semester: Optional[str] = None