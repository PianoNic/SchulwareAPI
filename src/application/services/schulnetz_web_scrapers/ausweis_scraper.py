"""Student ID card (Ausweis, pageid 50505) scraper → WebStudentIdCardDto.

The card renders via absolutely-positioned base64 images and inline CSS; a
structured table dump would lose the layout, so we return the raw body and let
the client render it.
"""

from src.application.dtos.web.scrape_dtos import WebStudentIdCardDto


def scrape_ausweis(html: str) -> WebStudentIdCardDto:
    return WebStudentIdCardDto(html=html)
