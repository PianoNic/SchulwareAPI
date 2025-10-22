from pydantic import BaseModel

class SettingDto(BaseModel):
    key: str | None = None
    value: str | None = None