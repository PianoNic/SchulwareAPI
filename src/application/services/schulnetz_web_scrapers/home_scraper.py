"""Home (dashboard) page scraper. Delegates to the universal extractor — every
table, key/value block, link, and image on the dashboard is pulled.

Sections on this page (as of Schulnetz 5.13): Ferienübersicht, Termine,
Ihre letzten Noten, Wichtige Direktlinks, Offene Absenzen, Angaben zum
Lehrbetrieb, Persönliche Angaben.
"""

from typing import Any

from src.application.services.schulnetz_web_scrapers._universal import scrape_schulnetz_page


def scrape_home(html: str) -> dict[str, Any]:
    return scrape_schulnetz_page(html)
