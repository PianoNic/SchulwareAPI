"""Absences (Absenzen) page scraper → typed AbsencesPageDto.

Layout: an absences table (11 columns), where each absence row is followed by a
single-cell row listing the per-lesson "Meldungen" for that absence, then a
standalone table of lesson reports (Datum / Zeit / Kurs / Bemerkung).
"""

import re

from bs4 import BeautifulSoup, Tag

from src.application.dtos.web.scrape_dtos import WebAbsenceDto, AbsenceReportDto, AbsencesPageDto

_ABSENCE_HEADER = "Datum von"
_REPORT_HEADER = "Datum"
# One Meldung: date, "HH:MM bis HH:MM", course token, remark (until next date/end).
_REPORT_RE = re.compile(
    r"(\d{2}\.\d{2}\.\d{4})\s+(\d{1,2}:\d{2}\s+bis\s+\d{1,2}:\d{2})\s+(\S+)\s+(.+?)(?=\d{2}\.\d{2}\.\d{4}\s+\d{1,2}:\d{2}|$)"
)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _int(text: str) -> int | None:
    m = re.search(r"-?\d+", text or "")
    return int(m.group()) if m else None


def _own_rows(table: Tag) -> list[Tag]:
    return [tr for tr in table.find_all("tr") if tr.find_parent("table") is table]


def _own_cells(row: Tag, table: Tag) -> list[str]:
    return [_clean(c.get_text()) for c in row.find_all(["th", "td"]) if c.find_parent("table") is table]


def _parse_reports(text: str) -> list[AbsenceReportDto]:
    return [
        AbsenceReportDto(date=d, time=_clean(t), course=c, remark=_clean(r))
        for d, t, c, r in _REPORT_RE.findall(text)
    ]


def _is_excused(value: str) -> bool | None:
    v = value.strip().lower()
    if v.startswith("ja"):
        return True
    if v.startswith("nein"):
        return False
    return None


def scrape_absences(html: str) -> AbsencesPageDto:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.body or soup

    heading = main.find(["h1", "h2", "h3"])
    student = None
    if heading:
        m = re.search(r"-\s*(.+)$", _clean(heading.get_text()))
        student = m.group(1) if m else None

    absences: list[WebAbsenceDto] = []
    lesson_reports: list[AbsenceReportDto] = []

    for table in main.find_all("table"):
        if table.find_parent("td"):
            continue
        rows = _own_rows(table)
        if not rows:
            continue
        header = _own_cells(rows[0], table)
        if not header:
            continue

        if header[0].startswith(_ABSENCE_HEADER):
            i = 1
            while i < len(rows):
                cells = _own_cells(rows[i], table)
                if len(cells) >= 11 and re.search(r"\d{2}\.\d{2}\.\d{4}", cells[0]):
                    absence = WebAbsenceDto(
                        date_from=cells[0] or None,
                        date_to=cells[1] or None,
                        reason=cells[2] or None,
                        additional_info=cells[3] or None,
                        extension_deadline=cells[4] or None,
                        status_eae=cells[5] or None,
                        excused=_is_excused(cells[6]),
                        lessons=_int(cells[7]),
                        comment=cells[8] or None,
                        trainer_comment=cells[9] or None,
                        acknowledged_at=cells[10] or None,
                    )
                    # The next single-cell row holds this absence's Meldungen.
                    if i + 1 < len(rows):
                        nxt = _own_cells(rows[i + 1], table)
                        if len(nxt) == 1 and "Meldungen" in nxt[0]:
                            absence.reports = _parse_reports(nxt[0])
                            i += 1
                    absences.append(absence)
                i += 1
        elif header[0] == _REPORT_HEADER and "Zeit" in header:
            for row in rows[1:]:
                cells = _own_cells(row, table)
                if len(cells) >= 4 and re.search(r"\d{2}\.\d{2}\.\d{4}", cells[0]):
                    lesson_reports.append(
                        AbsenceReportDto(date=cells[0] or None, time=cells[1] or None,
                                         course=cells[2] or None, remark=cells[3] or None)
                    )

    return AbsencesPageDto(student=student, absences=absences, lesson_reports=lesson_reports)
