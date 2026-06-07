"""Grades (Noten) page scraper → typed GradesPageDto.

The page is one outer table of courses (Kurs / Notendurchschnitt / Bestätigt).
Courses that have results carry a nested detail table of individual exams
(Datum / Thema / Bewertung / Gewichtung / Klassenschnitt), grouped under
"Einzelprüfungen" and ending in an "Aktueller Durchschnitt" summary row.
"""

import re

from bs4 import BeautifulSoup, Tag

from src.application.dtos.web.scrape_dtos import CourseGradesDto, ExamGradeDto, GradesPageDto

# A course cell starts with a course token like "GP-BM23d-ArAr" or "106-IN23a-ScPe".
_COURSE_RE = re.compile(r"^[A-Za-z0-9]+-[A-Za-z0-9]+-[A-Za-zÄÖÜäöü]+")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _num(text: str) -> float | None:
    m = re.search(r"-?\d+(?:\.\d+)?", text or "")
    return float(m.group()) if m else None


def _own_cells(row: Tag, table: Tag) -> list[Tag]:
    return [c for c in row.find_all(["th", "td"]) if c.find_parent("table") is table]


def _parse_exam_row(cells: list[str]) -> ExamGradeDto | None:
    # Exam rows look like ["", date, topic, mark(+points), weight, class_avg].
    # Drop a leading empty group cell so positions are stable.
    vals = cells[1:] if cells and not cells[0] else cells
    if len(vals) < 2:
        return None
    date, topic = vals[0], vals[1]
    if not re.match(r"\d{2}\.\d{2}\.\d{4}", date):
        return None
    mark_cell = vals[2] if len(vals) > 2 else ""
    points = None
    pm = re.search(r"Punkte:\s*(-?\d+(?:\.\d+)?)", mark_cell)
    if pm:
        points = float(pm.group(1))
    return ExamGradeDto(
        date=date,
        topic=topic or None,
        mark=_num(mark_cell.split("Details")[0]),
        points=points,
        weight=_num(vals[3]) if len(vals) > 3 else None,
        class_average=_num(vals[4]) if len(vals) > 4 else None,
    )


def _exams_from_detail(detail: Tag) -> list[ExamGradeDto]:
    exams: list[ExamGradeDto] = []
    for tr in detail.find_all("tr"):
        cells = [_clean(c.get_text()) for c in tr.find_all(["th", "td"])]
        if not cells:
            continue
        first = cells[0]
        if first in ("Prüfungsgruppe", "Einzelprüfungen") or first.startswith("Aktueller Durchschnitt"):
            continue
        exam = _parse_exam_row(cells)
        if exam:
            exams.append(exam)
    return exams


def scrape_noten(html: str) -> GradesPageDto:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.body or soup

    heading = main.find(["h1", "h2", "h3"])
    student = None
    if heading:
        m = re.search(r"-\s*(.+)$", _clean(heading.get_text()))
        student = m.group(1) if m else None

    outer = main.find("table")
    courses: list[CourseGradesDto] = []
    if outer is None:
        return GradesPageDto(student=student, courses=courses)

    # Map each nested detail table to the course row that precedes it.
    detail_by_course_id: dict[int, Tag] = {}
    for detail in outer.find_all("table"):
        row = detail.find_parent("tr")
        course_row = None
        while row is not None:
            row = row.find_previous_sibling("tr")
            if row is None:
                break
            cells = _own_cells(row, outer)
            if cells and _COURSE_RE.match(_clean(cells[0].get_text())) and row.find("table") is None:
                course_row = row
                break
        if course_row is not None:
            detail_by_course_id[id(course_row)] = detail

    for row in outer.find_all("tr"):
        if row.find_parent("table") is not outer:
            continue
        if row.find("table") is not None:
            continue
        cells = _own_cells(row, outer)
        if not cells:
            continue
        cell0 = cells[0]
        raw = _clean(cell0.get_text())
        if not _COURSE_RE.match(raw):
            continue
        # The course cell is "<b>{token}</b><br>{subject name}" — get_text()
        # smushes them together, so split the bold token off and keep the
        # human-readable subject name (fall back to the token if there's no name).
        bold = cell0.find("b")
        if bold is not None:
            token = _clean(bold.get_text())
            name = _clean(cell0.get_text(" ").replace(token, "", 1)) or token
        else:
            name = raw
        average = _num(_clean(cells[1].get_text())) if len(cells) > 1 else None
        row_text = _clean(row.get_text())
        confirmed = "bestätigt" in row_text.lower() and "bestätigen" not in row_text.lower()
        detail = detail_by_course_id.get(id(row))
        exams = _exams_from_detail(detail) if detail is not None else []
        courses.append(CourseGradesDto(course=name, average=average, confirmed=confirmed, exams=exams))

    return GradesPageDto(student=student, courses=courses)
