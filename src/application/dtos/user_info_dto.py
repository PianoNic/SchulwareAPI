from dataclasses import dataclass, field
from typing import Optional, List
from src.application.dtos.class_info_dto import ClassInfoDto

@dataclass
class UserInfoDto:
    id: str
    userType: str
    idNr: str
    lastName: str
    firstName: str
    loginActive: bool
    gender: str
    birthday: str
    street: str
    addressLine2: Optional[str]
    postOfficeBox: Optional[str]
    zip: str
    city: str
    nationality: str
    hometown: str
    phone: str
    mobile: str
    email: str
    emailPrivate: str
    profil1: str
    profil2: str
    entryDate: str
    exitDate: str
    regularClasses: List[ClassInfoDto] = field(default_factory=list)
    additionalClasses: List[ClassInfoDto] = field(default_factory=list)

