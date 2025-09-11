from pydantic import BaseModel

class AppInfoDto(BaseModel):
    """Data Transfer Object for application information"""
    version: str
    environment: str