"""Agenda page scraper.

The agenda page is JS-driven (scheduler widget); its actual events come from
`scheduler_processor.php` parsed by `schedule_scraper.parse_scheduler_xml`.
This scraper still runs the universal extractor so the static surface
(headings, links, any tables Schulnetz may render statically) is captured —
but the meaningful per-event data lives in the `schedule` page.
"""

from typing import Any

from src.application.services.schulnetz_web_scrapers._universal import scrape_schulnetz_page


def scrape_agenda(html: str) -> dict[str, Any]:
    return scrape_schulnetz_page(html)
