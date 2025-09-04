from dataclasses import dataclass

@dataclass
class EventDto:
    date: str
    time: str
    time_until: str
    location: str
    description: str
    info: str