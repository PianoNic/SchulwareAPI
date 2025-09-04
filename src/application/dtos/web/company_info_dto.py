from dataclasses import dataclass
from typing import Optional

@dataclass
class CompanyInfoDto:
    name: Optional[str] = None
    street: Optional[str] = None
    postal_city: Optional[str] = None
    trainer: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None