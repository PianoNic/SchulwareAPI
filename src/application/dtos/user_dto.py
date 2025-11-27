from pydantic import BaseModel

class UserDto(BaseModel):
    email: str