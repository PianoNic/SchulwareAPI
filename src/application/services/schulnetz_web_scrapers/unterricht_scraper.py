"""Lessons (Unterricht, pageid 21355) scraper → typed LessonsPageDto.

Tables of lesson entries (Kurs / Titel / Beschreibung / Datum / Zeit, with an
optional "Übersteuerter Betrag" column on the billing variant).
"""

import re

from bs4 import BeautifulSoup, Tag

from src.application.dtos.web.scrape_dtos import LessonDto, LessonsPageDto

_COLUMN_MAP = {
    "Kurs": "course",
    "Titel": "title",
    "Beschreibung": "description",
    "Datum": "date",
    "Zeit": "time",
    "Übersteuerter Betrag": "overridden_amount",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _own_rows(table: Tag) -> list[Tag]:
    return [tr for tr in table.find_all("tr") if tr.find_parent("table") is table]


def scrape_unterricht(html: str) -> LessonsPageDto:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.body or soup

    lessons: list[LessonDto] = []
    for table in main.find_all("table"):
        if table.find_parent("td"):
            continue
        rows = _own_rows(table)
        if not rows:
            continue
        headers = [_clean(c.get_text()) for c in rows[0].find_all(["th", "td"])]
        field_at = {i: _COLUMN_MAP[h] for i, h in enumerate(headers) if h in _COLUMN_MAP}
        if "course" not in field_at.values():
            continue
        for row in rows[1:]:
            texts = [_clean(c.get_text()) for c in row.find_all(["td", "th"])]
            if not any(texts) or all(t in ("", "Suchtext") for t in texts):
                continue
            if texts and texts[0].startswith("Keine Einträge"):
                continue
            data = {field: (texts[i] or None) for i, field in field_at.items() if i < len(texts)}
            if any(data.values()):
                lessons.append(LessonDto(**data))

    return LessonsPageDto(lessons=lessons)
