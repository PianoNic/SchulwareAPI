from pydantic import BaseModel

class FilestoreFileDto(BaseModel):
    id: str | None = None
    name: str | None = None
    content: str | None = None
    """The file as a data URI, e.g. `data:application/pdf;base64,...`."""


class FilestoreEntryDto(BaseModel):
    """A document from /me/filestore, with its file inline."""
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
    file: FilestoreFileDto | None = None
