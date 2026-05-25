"""Universal Schulnetz page scraper.

Schulnetz dashboard pages are built from a fixed pattern:
  - A page-level `<h3>` heading at the top of the content area.
  - One or more `<table>` blocks, each preceded by its own `<h3>`/`<h4>` heading.
  - Some pages also embed key/value tables (label cell + value cell, no
    `<th>` header row) — e.g. "Persönliche Angaben", "Angaben zum Lehrbetrieb".
  - A few pages (student ID, document landing pages) carry their data in
    images or anchors instead of tables.

Instead of hand-coding a brittle parser per page (the original approach),
this function pulls EVERYTHING into a structured dict that callers can pick
from:

    {
      "page_heading": "Start",
      "tables": [
        {
          "name": "Ferienübersicht",                # nearest preceding heading
          "columns": ["Bezeichnung", "Von", "Bis"],
          "rows": [
            {"Bezeichnung": "Fronleichnam 2026",
             "Von":         "04.06.2026",
             "Bis":         "04.06.2026"},
            ...
          ],
        },
        ...
      ],
      "key_value_blocks": {
        "Persönliche Angaben": {"Name Vorname": "...", "Strasse": "...", ...},
        "Angaben zum Lehrbetrieb": {...},
      },
      "links": [{"text": "Zur Terminliste", "href": "index.php?pageid=22108&..."}, ...],
      "images": [{"alt": "Left Image", "src": "data:image/png;base64,..."}, ...],
    }
"""

import re
from typing import Any

from bs4 import BeautifulSoup, Tag


def scrape_schulnetz_page(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.body or soup

    return {
        "page_heading": _first_text(main, ["h3", "h2", "h1"]),
        "tables": _extract_tables(main),
        "key_value_blocks": _extract_kv_blocks(main),
        "links": _extract_content_links(main),
        "images": _extract_images(main),
    }


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _first_text(root: Tag, selectors: list[str]) -> str | None:
    for sel in selectors:
        el = root.select_one(sel)
        if el:
            text = _clean(el.get_text())
            if text:
                return text
    return None


def _nearest_preceding_heading(table: Tag) -> str | None:
    """Closest <h3>/<h2>/<h1>/<h4> earlier in document order."""
    prev = table.find_previous(["h3", "h4", "h2", "h1"])
    return _clean(prev.get_text()) if prev else None


def _first_row_is_header(rows_html: list[Tag]) -> bool:
    """A table is 'header + data' when its first row uses any <th> cells."""
    if not rows_html:
        return False
    return any(c.name == "th" for c in rows_html[0].find_all(["th", "td"]))


def _looks_like_kv_table(rows_html: list[Tag], tbl: Tag) -> bool:
    """Two-column 'label / value' table without a header row.

    `tbl` is the owning <table>; we only count cells whose nearest table
    ancestor is `tbl`, so nested decorative cells don't break the check.
    """
    if _first_row_is_header(rows_html):
        return False
    if len(rows_html) < 1:
        return False
    for tr in rows_html:
        cells = [c for c in tr.find_all(["th", "td"]) if c.find_parent("table") is tbl]
        if len(cells) != 2:
            return False
        if not _clean(cells[0].get_text()):
            return False
    return True


def _own_rows(tbl: Tag) -> list[Tag]:
    """Rows that belong directly to `tbl`, not to any nested `<table>` inside it.

    `find_all('tr')` is recursive and would also return rows from inner tables
    nested in a `<td>`. The grades page has detail-table rows nested under each
    course row — without this filter, the outer table's `rows` get polluted by
    every inner exam row, mis-counting and mis-aligning data.
    """
    return [tr for tr in tbl.find_all("tr") if tr.find_parent("table") is tbl]


def _extract_tables(root: Tag) -> list[dict[str, Any]]:
    out = []
    for tbl in root.find_all("table"):
        # Skip tables nested inside other table cells — those are usually
        # decorative groupings within an outer data table.
        if tbl.find_parent("td"):
            continue

        rows_html = _own_rows(tbl)
        if not rows_html:
            continue

        # Only treat the first row as a column-header row when it actually
        # uses <th>. Tables without a <th> row (e.g. the home page's
        # "Ihre letzten Noten" preview) have no semantic columns, so we keep
        # `columns` empty and return rows with positional keys instead of
        # mis-labelling data cells as headers.
        if _first_row_is_header(rows_html):
            header_cells = rows_html[0].find_all(["th", "td"])
            columns = [_clean(c.get_text()) for c in header_cells]
            data_rows = rows_html[1:]
        else:
            columns = []
            data_rows = rows_html

        rows: list[dict[str, str]] = []
        for tr in data_rows:
            # Only THIS table's direct cells, not cells from inner nested tables.
            own_cells = [c for c in tr.find_all(["th", "td"]) if c.find_parent("table") is tbl]
            cells = [_clean(c.get_text()) for c in own_cells]
            if not any(cells):
                continue
            if columns:
                row = {}
                for i, val in enumerate(cells):
                    row[columns[i] if i < len(columns) else str(i)] = val
                rows.append(row)
            else:
                rows.append({str(i): v for i, v in enumerate(cells)})

        out.append({
            "name": _nearest_preceding_heading(tbl),
            "columns": columns,
            "rows": rows,
        })
    return out


def _extract_kv_blocks(root: Tag) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for tbl in root.find_all("table"):
        if tbl.find_parent("td"):
            continue
        rows_html = _own_rows(tbl)
        if not _looks_like_kv_table(rows_html, tbl):
            continue
        kv: dict[str, str] = {}
        for tr in rows_html:
            cells = [c for c in tr.find_all(["th", "td"]) if c.find_parent("table") is tbl]
            kv[_clean(cells[0].get_text())] = _clean(cells[1].get_text())
        name = _nearest_preceding_heading(tbl) or "Unbenannt"
        # If two sections share the same heading (shouldn't happen on Schulnetz
        # but be safe), keep them all.
        if name in out:
            out[f"{name} ({len(out)})"] = kv
        else:
            out[name] = kv
    return out


def _extract_content_links(root: Tag) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, str]] = []
    for a in root.find_all("a", href=True):
        href = a["href"]
        if not href or href in ("#", "#!"):
            continue
        text = _clean(a.get_text())
        if not text:
            continue
        key = (text, href)
        if key in seen:
            continue
        seen.add(key)
        out.append({"text": text, "href": href})
    return out


def _extract_images(root: Tag) -> list[dict[str, str]]:
    out = []
    for img in root.find_all("img"):
        src = img.get("src", "")
        if not src:
            continue
        out.append({
            "alt": img.get("alt", ""),
            "src": src,
        })
    return out
