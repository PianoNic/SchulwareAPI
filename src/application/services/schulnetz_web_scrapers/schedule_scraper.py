import xml.etree.ElementTree as ET
from typing import List, Dict, Optional


def parse_scheduler_xml(xml_text: str) -> List[Dict[str, Optional[str]]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    events = []
    for event_el in root.findall("event"):
        event = {}
        fields = [
            "start_date", "end_date", "text", "kommentar", "klasse",
            "zimmer", "zimmerkuerzel", "lehrerkuerzelname", "kurskuerzel",
            "kursid", "color", "event_type", "fachkuerzel", "wochentag",
            "lektionswert", "kalenderwoche", "schulanlage",
        ]
        for field in fields:
            el = event_el.find(field)
            if el is not None and el.text:
                event[field] = el.text.strip()

        event_id = event_el.get("id")
        if event_id:
            event["id"] = event_id

        if event.get("start_date"):
            events.append(event)

    return events
