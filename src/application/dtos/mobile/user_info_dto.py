from pydantic import BaseModel, Field
from src.application.dtos.mobile.class_info_dto import ClassInfoDto

class UserInfoDto(BaseModel):
    id: str | None = None
    userType: str | None = None
    idNr: str | None = None
    lastName: str | None = None
    firstName: str | None = None
    loginActive: bool | None = None
    gender: str | None = None
    birthday: str | None = None
    street: str | None = None
    addressLine2: str | None = None
    postOfficeBox: str | None = None
    zip: str | None = None
    city: str | None = None
    nationality: str | None = None
    hometown: str | None = None
    phone: str | None = None
    mobile: str | None = None
    email: str | None = None
    emailPrivate: str | None = None
    profil1: str | None = None
    profil2: str | None = None
    entryDate: str | None = None
    exitDate: str | None = None
    regularClasses: list[ClassInfoDto] | None = None
    additionalClasses: list[ClassInfoDto] | None = None

