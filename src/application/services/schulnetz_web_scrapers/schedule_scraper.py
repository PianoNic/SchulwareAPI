"""Scheduler XML parser (scheduler_processor.php) → typed ScheduleEventDto list.

This is the meaningful agenda data: each `<event>` is a lesson/appointment with
times, room, teacher, course, etc.
"""

import xml.etree.ElementTree as ET

from src.application.dtos.web.scrape_dtos import ScheduleEventDto

_FIELDS = [
    "start_date", "end_date", "text", "kommentar", "klasse",
    "zimmer", "zimmerkuerzel", "lehrerkuerzelname", "kurskuerzel",
    "kursid", "color", "event_type", "fachkuerzel", "wochentag",
    "lektionswert", "kalenderwoche", "schulanlage",
]


def parse_scheduler_xml(xml_text: str) -> list[ScheduleEventDto]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    events: list[ScheduleEventDto] = []
    for event_el in root.findall("event"):
        values: dict[str, str | None] = {}
        for field in _FIELDS:
            el = event_el.find(field)
            if el is not None and el.text:
                values[field] = el.text.strip()
        event_id = event_el.get("id")
        if event_id:
            values["id"] = event_id
        if values.get("start_date"):
            events.append(ScheduleEventDto(**values))

    return events
