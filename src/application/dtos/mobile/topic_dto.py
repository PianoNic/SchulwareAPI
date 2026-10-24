from pydantic import BaseModel

class TopicDto(BaseModel):
    id: str | None = None
    title: str | None = None
    comment: str | None = None
    mailEnabled: bool | None = None
    appEnabled: bool | None = None
    pushEnabled: bool | None = None
    mandatory: bool | None = None
    mailSubscribed: bool | None = None
    appSubscribed: bool | None = None
    pushSubscribed: bool | None = None
