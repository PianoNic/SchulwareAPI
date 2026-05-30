"""Agenda (pageid 21200) scraper → typed AgendaPageDto.

The agenda page is JS-driven (scheduler widget); the real per-event data comes
from `scheduler_processor.php` and is parsed by `schedule_scraper.parse_scheduler_xml`
(the `schedule` page). This scraper extracts any events Schulnetz renders into
the static HTML; in practice the page ships empty and clients should use the
`schedule` page for the events.
"""

from src.application.dtos.web.scrape_dtos import AgendaPageDto


def scrape_agenda(html: str) -> AgendaPageDto:
    # The static agenda HTML carries no event rows (the widget loads them via XML).
    return AgendaPageDto(events=[])
