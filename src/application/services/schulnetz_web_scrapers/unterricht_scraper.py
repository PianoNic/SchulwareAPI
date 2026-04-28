import re
from bs4 import BeautifulSoup
from typing import List, Dict


def scrape_unterricht(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    lessons = []

    for table in soup.find_all("table"):
        header_row = table.find("tr")
        if not header_row:
            continue

        headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
        if not headers or "Kurs" not in headers:
            continue

        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            if row.find("input"):
                continue

            item = {}
            for i, h in enumerate(headers):
                if i < len(cells):
                    text = re.sub(r'\s+', ' ', cells[i].get_text()).strip()
                    item[h] = text

            if any(v and v != "Keine Einträge" for v in item.values()):
                lessons.append(item)

    return lessons
