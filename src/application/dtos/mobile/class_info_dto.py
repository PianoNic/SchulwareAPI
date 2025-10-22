from pydantic import BaseModel

class ClassInfoDto(BaseModel):
    id: str | None = None
    token: str | None = None
    semester: str | None = None