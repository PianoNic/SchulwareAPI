"""Lists & Documents (Listen&Dokumente) page scraper.

This page is a nav landing — its data lives in the `links` field (sub-pages
like "Lehrpersonenliste", "Meine Kurse", "Lernendenübersicht", "Persönliches
Dossier"). Delegates to the universal extractor.
"""

from typing import Any

from src.application.services.schulnetz_web_scrapers._universal import scrape_schulnetz_page


def scrape_listen(html: str) -> dict[str, Any]:
    return scrape_schulnetz_page(html)
