"""Grades page scraper. Delegates to the universal extractor — every grade
table (course averages + per-Prüfungsgruppe exam details) is pulled.
"""

from typing import Any

from src.application.services.schulnetz_web_scrapers._universal import scrape_schulnetz_page


def scrape_noten(html: str) -> dict[str, Any]:
    return scrape_schulnetz_page(html)
