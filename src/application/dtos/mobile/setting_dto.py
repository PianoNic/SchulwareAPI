from pydantic import BaseModel

class SettingDto(BaseModel):
    key: str
    value: str