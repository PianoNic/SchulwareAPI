from bs4 import BeautifulSoup
from typing import List, Dict, Any


def scrape_home(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    return {
        "holidays": _parse_table_by_heading(soup, "Ferienübersicht", ["name", "from", "to"]),
        "events": _parse_table_by_heading(soup, "Termine", ["date", "time", "time_to", "location", "description", "info"]),
        "recent_grades": _parse_table_by_heading(soup, "Ihre letzten Noten", ["course", "exam", "date", "grade"]),
        "open_absences": _parse_table_by_heading(soup, "Offene Absenzen", ["from", "to", "excuse_deadline", "status"]),
        "personal_info": _parse_key_value_table(soup, "Persönliche Angaben"),
        "employer_info": _parse_key_value_table(soup, "Angaben zum Lehrbetrieb"),
    }


def _parse_table_by_heading(soup: BeautifulSoup, heading: str, field_names: List[str]) -> List[Dict[str, str]]:
    h3 = soup.find("h3", string=lambda t: t and heading in t)
    if not h3:
        return []

    table = h3.find_next("table")
    if not table:
        return []

    items = []
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if not cells or len(cells) < 2:
            continue
        item = {}
        for i, name in enumerate(field_names):
            if i < len(cells):
                item[name] = cells[i].get_text(strip=True)
        items.append(item)

    return items


def _parse_key_value_table(soup: BeautifulSoup, heading: str) -> Dict[str, str]:
    h3 = soup.find("h3", string=lambda t: t and heading in t)
    if not h3:
        return {}

    table = h3.find_next("table")
    if not table:
        return {}

    info = {}
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) >= 2:
            key = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)
            if key:
                info[key] = value

    return info
