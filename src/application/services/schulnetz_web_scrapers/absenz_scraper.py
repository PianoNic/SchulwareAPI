"""Absences page scraper. Delegates to the universal extractor — open
absences, confirmed absences, summary counters, lateness, and any extra
sections are all pulled.
"""

from typing import Any

from src.application.services.schulnetz_web_scrapers._universal import scrape_schulnetz_page


def scrape_absences(html: str) -> dict[str, Any]:
    return scrape_schulnetz_page(html)
