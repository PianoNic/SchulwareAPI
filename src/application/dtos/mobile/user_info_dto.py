from typing import Optional, List
from pydantic import BaseModel, Field
from src.application.dtos.mobile.class_info_dto import ClassInfoDto

class UserInfoDto(BaseModel):
    id: str
    userType: str
    idNr: str
    lastName: str
    firstName: str
    loginActive: bool
    gender: str
    birthday: str
    street: str
    addressLine2: Optional[str] = None
    postOfficeBox: Optional[str] = None
    zip: str
    city: str
    nationality: str
    hometown: str
    phone: str
    mobile: str
    email: str
    emailPrivate: str
    profil1: str
    profil2: Optional[str] = None
    entryDate: str
    exitDate: str
    regularClasses: List[ClassInfoDto] = Field(default_factory=list)
    additionalClasses: List[ClassInfoDto] = Field(default_factory=list)

