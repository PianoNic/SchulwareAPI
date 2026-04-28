import re
from bs4 import BeautifulSoup
from typing import List, Dict


def scrape_listen(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    documents = []

    for table in soup.find_all("table"):
        header_row = table.find("tr")
        if not header_row:
            continue

        headers = [re.sub(r'\s+', ' ', h.get_text()).strip() for h in header_row.find_all(["th", "td"])]
        if "Titel" not in headers:
            continue

        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            if row.find("input"):
                continue

            title_idx = headers.index("Titel") if "Titel" in headers else 1
            title = re.sub(r'\s+', ' ', cells[title_idx].get_text()).strip() if title_idx < len(cells) else ""

            if not title or title == "Suchtext" or title.startswith("Volltextsuche"):
                continue
            if title in ("Summe", "Min", "Max", "Durchschn."):
                continue

            doc = {"title": title}

            field_map = {
                "Kommentar": "comment",
                "Erfasst am": "created_at",
                "Erfasst von": "created_by",
                "Aktualisiert am": "updated_at",
                "Kategorie": "category",
                "Datei": "filename",
                "Grösse": "size",
            }

            for header_name, field_name in field_map.items():
                if header_name in headers:
                    idx = headers.index(header_name)
                    if idx < len(cells):
                        doc[field_name] = re.sub(r'\s+', ' ', cells[idx].get_text()).strip()

            link = row.find("a", href=True)
            if link:
                doc["url"] = link.get("href")

            documents.append(doc)

    if not documents:
        for link in soup.find_all("a"):
            href = link.get("href", "")
            text = link.get_text(strip=True)
            if text and href and ("pageid=10053" in href or "download" in href.lower()):
                documents.append({"title": text, "url": href})

    return documents
