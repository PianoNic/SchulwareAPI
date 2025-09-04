from dataclasses import dataclass
from typing import Optional

@dataclass
class PersonalInfoDto:
    full_name: Optional[str] = None
    street: Optional[str] = None
    postal_city: Optional[str] = None
    birthdate: Optional[str] = None
    education: Optional[str] = None
    contract_number: Optional[str] = None
    hometown: Optional[str] = None
    phone: Optional[str] = None
    mobile_phone: Optional[str] = None