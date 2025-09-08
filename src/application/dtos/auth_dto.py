from pydantic import BaseModel

class MobileSessionDto(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int

class WebSessionDto(BaseModel):
    php_session_id: str

class SessionDto(BaseModel):
    mobile_session_dto: MobileSessionDto
    web_session_dto: WebSessionDto