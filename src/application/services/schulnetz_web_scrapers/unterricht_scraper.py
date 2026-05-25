"""Lessons (Unterricht) page scraper. Delegates to the universal extractor."""

from typing import Any

from src.application.services.schulnetz_web_scrapers._universal import scrape_schulnetz_page


def scrape_unterricht(html: str) -> dict[str, Any]:
    return scrape_schulnetz_page(html)
