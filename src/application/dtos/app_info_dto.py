from pydantic import BaseModel

class AppInfoDto(BaseModel):
    version: str
    environment: str