from pydantic import BaseModel

class ClassInfoDto(BaseModel):
    id: str
    token: str
    semester: str