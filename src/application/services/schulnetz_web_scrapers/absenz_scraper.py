import re
from bs4 import BeautifulSoup
from typing import List, Dict, Any


def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def scrape_absences(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    absences = []
    summaries = []
    lateness = []

    tables = soup.find_all("table")
    for table in tables:
        header_row = table.find("tr")
        if not header_row:
            continue

        headers = [_clean(th.get_text()) for th in header_row.find_all(["th", "td"])]

        if "Datum von" in headers:
            for row in table.find_all("tr")[1:]:
                cells = row.find_all("td")
                if len(cells) < 7:
                    continue

                if row.find("table"):
                    continue

                date_from = _clean(cells[0].get_text())
                if not date_from or "Anzahl" in date_from or "Meldungen" in date_from:
                    continue

                absences.append({
                    "date_from": date_from,
                    "date_to": _clean(cells[1].get_text()),
                    "reason": _clean(cells[2].get_text()),
                    "additional_info": _clean(cells[3].get_text()),
                    "additional_days": _clean(cells[4].get_text()),
                    "status_eae": _clean(cells[5].get_text()),
                    "excused": _clean(cells[6].get_text()),
                    "lessons": _clean(cells[7].get_text()) if len(cells) > 7 else "",
                    "comment": _clean(cells[8].get_text()) if len(cells) > 8 else "",
                    "employer_comment": _clean(cells[9].get_text()) if len(cells) > 9 else "",
                    "confirmed_at": _clean(cells[10].get_text()) if len(cells) > 10 else "",
                })

        elif headers and "Anzahl Ereignisse" in headers[0]:
            summary_text = " ".join(headers)
            events_match = re.search(r"Anzahl Ereignisse:\s*(\d+)", summary_text)
            excused_match = re.search(r"Lektionen entschuldigt:\s*(\d+)", summary_text)
            unexcused_match = re.search(r"Lektionen unentschuldigt:\s*(\d+)", summary_text)
            summaries.append({
                "total_events": int(events_match.group(1)) if events_match else 0,
                "lessons_excused": int(excused_match.group(1)) if excused_match else 0,
                "lessons_unexcused": int(unexcused_match.group(1)) if unexcused_match else 0,
            })

        elif headers == ["Datum", "Zeit", "Kurs", "Bemerkung"]:
            for row in table.find_all("tr")[1:]:
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue

                if row.find("table"):
                    continue

                date = _clean(cells[0].get_text())
                if not date or "Anzahl" in date:
                    continue

                lateness.append({
                    "date": date,
                    "time": _clean(cells[1].get_text()),
                    "course": _clean(cells[2].get_text()),
                    "remark": _clean(cells[3].get_text()),
                })

    summary = summaries[0] if summaries else {"total_events": len(absences), "lessons_excused": 0, "lessons_unexcused": 0}

    return {"absences": absences, "lateness": lateness, "summary": summary}
