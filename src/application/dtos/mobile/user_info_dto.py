from typing import Optional
from pydantic import BaseModel, Field
from src.application.dtos.mobile.class_info_dto import ClassInfoDto

class UserInfoDto(BaseModel):
    id: Optional[str] = None
    userType: Optional[str] = None
    idNr: Optional[str] = None
    lastName: Optional[str] = None
    firstName: Optional[str] = None
    loginActive: Optional[bool] = None
    gender: Optional[str] = None
    birthday: Optional[str] = None
    street: Optional[str] = None
    addressLine2: Optional[str] = None
    postOfficeBox: Optional[str] = None
    zip: Optional[str] = None
    city: Optional[str] = None
    nationality: Optional[str] = None
    hometown: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    emailPrivate: Optional[str] = None
    profil1: Optional[str] = None
    profil2: Optional[str] = None
    entryDate: Optional[str] = None
    exitDate: Optional[str] = None
    regularClasses: Optional[list[ClassInfoDto]] = None
    additionalClasses: Optional[list[ClassInfoDto]] = None

