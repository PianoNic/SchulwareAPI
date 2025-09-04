from dataclasses import dataclass

@dataclass
class MobileSessionDto:
    access_token: str
    refresh_token: str
    expires_in: str

@dataclass
class WebSessionDto:
    php_session_id: str
    
@dataclass
class SessionDto:
    mobile_session_dto: MobileSessionDto
    web_session_dto: WebSessionDto