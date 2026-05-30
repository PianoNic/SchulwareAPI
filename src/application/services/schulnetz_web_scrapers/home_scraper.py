"""Home (dashboard, pageid 1) scraper → typed HomePageDto.

The dashboard aggregates many heterogeneous sections (Ferienübersicht, Termine,
Ihre letzten Noten, Wichtige Direktlinks, Offene Absenzen, Angaben zum
Lehrbetrieb, Persönliche Angaben), so it keeps the universal extractor's
structure — now wrapped in a typed model.
"""

from src.application.dtos.web.scrape_dtos import (
    HomePageDto,
    ScrapedImageDto,
    ScrapedLinkDto,
    ScrapedTableDto,
)
from src.application.services.schulnetz_web_scrapers._universal import scrape_schulnetz_page


def scrape_home(html: str) -> HomePageDto:
    raw = scrape_schulnetz_page(html)
    return HomePageDto(
        page_heading=raw.get("page_heading"),
        tables=[ScrapedTableDto(**t) for t in raw.get("tables", [])],
        key_value_blocks=raw.get("key_value_blocks", {}),
        links=[ScrapedLinkDto(**l) for l in raw.get("links", [])],
        images=[ScrapedImageDto(**i) for i in raw.get("images", [])],
    )
