"""Documents / files (Persönliches Dossier, pageid 10053) scraper → DocumentsPageDto.

The page is a single table of stored files. Each row carries a download link
(pageid=10051&tblName=tblFilestore&listindex=N) plus metadata columns
(Titel, Kategorie, Datei, Grösse, …).
"""

import re

from bs4 import BeautifulSoup, Tag

from src.application.dtos.web.scrape_dtos import DocumentFileDto, DocumentsPageDto

_COLUMN_MAP = {
    "Titel": "title",
    "Kommentar": "comment",
    "Erfasst am": "created_at",
    "Erfasst von": "created_by",
    "Aktualisiert am": "updated_at",
    "Kategorie": "category",
    "Datei": "filename",
    "Grösse": "size",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _own_rows(table: Tag) -> list[Tag]:
    return [tr for tr in table.find_all("tr") if tr.find_parent("table") is table]


def scrape_listen(html: str) -> DocumentsPageDto:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.body or soup

    table = main.find("table")
    files: list[DocumentFileDto] = []
    if table is None:
        return DocumentsPageDto(files=files)

    rows = _own_rows(table)
    if not rows:
        return DocumentsPageDto(files=files)

    headers = [_clean(c.get_text()) for c in rows[0].find_all(["th", "td"])]
    field_at = {i: _COLUMN_MAP[h] for i, h in enumerate(headers) if h in _COLUMN_MAP}

    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        texts = [_clean(c.get_text()) for c in cells]
        # Skip the filter ("Suchtext") and full-text-search helper rows.
        if not any(texts) or any("Suchtext" in t for t in texts):
            continue
        if any("Volltextsuche" in t for t in texts):
            continue

        data = {field: (texts[i] or None) for i, field in field_at.items() if i < len(texts)}
        if not data.get("filename") and not data.get("title"):
            continue

        # The download link is the first anchor pointing at the filestore export page.
        download = None
        for a in (cells[0].find_all("a", href=True) if cells else []):
            if "10051" in a["href"] or "wkhtml" in a["href"] or "export" in a["href"]:
                download = a["href"]
                break
        if download is None and cells:
            anchor = cells[0].find("a", href=True)
            download = anchor["href"] if anchor else None

        files.append(DocumentFileDto(download_url=download, **data))

    return DocumentsPageDto(files=files)
