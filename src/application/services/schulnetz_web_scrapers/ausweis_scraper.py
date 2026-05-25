"""Student ID card (Ausweis) page scraper.

The student ID page renders the card with absolutely-positioned base64
images and inline CSS — losing that layout to a structured table dump would
break rendering in any client that just wants to display the card. So this
scraper returns the raw HTML body and lets the client decide how to render.
"""

from typing import Any


def scrape_ausweis(html: str) -> dict[str, Any]:
    return {"html": html}
