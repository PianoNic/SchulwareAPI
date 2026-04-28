import re
from bs4 import BeautifulSoup
from typing import List, Dict, Any


def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def scrape_noten(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    courses = []
    table = soup.find("table")
    if not table:
        return {"courses": [], "exam_details": []}

    for row in table.find_all("tr"):
        cells = row.find_all("td")
        cls = " ".join(row.get("class", []))

        if "detailrow" in cls or not cells or len(cells) < 2:
            continue

        course_text = _clean(cells[0].get_text())
        if not course_text:
            continue

        average = _clean(cells[1].get_text()) if len(cells) > 1 else "--"
        confirmed = _clean(cells[2].get_text()) if len(cells) > 2 else ""

        courses.append({
            "course": course_text,
            "average": average if average != "--" else None,
            "confirmed": confirmed if confirmed else None,
        })

    exam_details = []
    for dt in soup.find_all("table")[1:]:
        header_row = dt.find("tr")
        if not header_row:
            continue

        headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
        if "Datum" not in " ".join(headers):
            continue

        for row in dt.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            date = _clean(cells[1].get_text())
            topic = _clean(cells[2].get_text())
            if not date and not topic:
                continue

            grade_text = _clean(cells[3].get_text())
            grade_match = re.search(r'\d+\.\d+|\d+', grade_text)

            exam_details.append({
                "group": _clean(cells[0].get_text()),
                "date": date,
                "topic": topic,
                "grade": grade_match.group() if grade_match else None,
                "weight": _clean(cells[4].get_text()) if len(cells) > 4 else "",
                "class_average": _clean(cells[5].get_text()) if len(cells) > 5 else None,
            })

    return {"courses": courses, "exam_details": exam_details}
