from typing import Optional
from pydantic import BaseModel

class SettingDto(BaseModel):
    key: Optional[str] = None
    value: Optional[str] = None