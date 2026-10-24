from pydantic import BaseModel

class FilestoreEntryDto(BaseModel):
    """A document from /me/filestore. `file` is the content, base64-encoded."""
    id: str | None = None
    title: str | None = None
    comment: str | None = None
    category: str | None = None
    date: str | None = None
    dateCreatedOn: str | None = None
    followUp: str | None = None
    followUpDate: str | None = None
    followUpPerformedDate: str | None = None
    private: str | None = None
    file: str | None = None
