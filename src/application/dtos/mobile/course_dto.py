from pydantic import BaseModel

class CourseDto(BaseModel):
    id: str | None = None
    token: str | None = None
    name: str | None = None
    semester: int | None = None
    isMarkRelevant: bool | None = None
