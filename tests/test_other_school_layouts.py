"""Schools lay out the grades and absences pages differently; both scrapers must read them by structure and heading."""

from src.application.services.schulnetz_web_scrapers.absenz_scraper import scrape_absences
from src.application.services.schulnetz_web_scrapers.noten_scraper import scrape_noten


def _detail(*topics):
    rows = "".join(f"<tr><td></td><td>01.09.2026</td><td>{t}</td><td>5.5</td><td>1</td><td>4.8</td></tr>" for t in topics)
    return f"<tr><td colspan='5'><table><tr><td>Prüfungsgruppe</td><td>Datum</td><td>Thema</td></tr>{rows}</table></td></tr><tr><td></td></tr>"


GRADES = (
    "<main><h3>Noten - Muster Mia (G4d)</h3><table>"
    "<tr><td>Kurs</td><td>Notendurchschnitt</td><td>Bestätigt</td><td></td></tr>"
    "<tr><td><b>DEU-G4d-AbC</b><br>Deutsch</td><td>5.000</td><td></td><td></td><td></td></tr>" + _detail("Lyrik")
    + "<tr><td><b>Einf.4.1 (EF)</b><br>Informatik</td><td>6.000</td><td></td><td></td><td></td></tr>" + _detail("Python", "OOP")
    + "<tr><td><b>Fpol.0.1 (FF)</b><br>Politik</td><td>--</td><td></td><td></td><td></td></tr><tr><td></td></tr>"
    + "<tr><td><b>spm.4.d (SPO)</b><br>Sport</td><td>3.750</td><td></td><td></td><td></td></tr>" + _detail("Ausdauer")
    + "</table></main>"
)


def test_every_course_code_style_is_read_and_keeps_its_own_exams():
    courses = {c.course: c for c in scrape_noten(GRADES).courses}
    assert list(courses) == ["Deutsch", "Informatik", "Politik", "Sport"]
    assert [e.topic for e in courses["Deutsch"].exams] == ["Lyrik"]
    assert [e.topic for e in courses["Informatik"].exams] == ["Python", "OOP"]
    assert courses["Politik"].average is None and courses["Politik"].exams == []
    assert [e.topic for e in courses["Sport"].exams] == ["Ausdauer"]


ABSENCES = (
    "<main><h3>Absenzen - Muster Mia (G4d)</h3><table>"
    "<tr><td>Datum von</td><td>Datum bis</td><td>Grund</td><td>Absenzpunkte</td><td>Kommentar</td></tr>"
    "<tr><td>17.08.2026</td><td>17.08.2026</td><td>Arzt</td><td>3 Zu dieser Absenz erfassten Meldungen: "
    "17.08.2026, von 13:30 bis 14:15, fra-F.4.d 17.08.2026, von 14:25 bis 15:10, fra-F.4.d</td><td></td></tr>"
    "<tr><td>25.08.2026</td><td>26.08.2026</td><td></td><td>0</td><td>ok</td></tr>"
    "</table></main>"
)


def test_a_points_layout_is_read_by_its_headings():
    first, second = scrape_absences(ABSENCES).absences
    assert (first.date_from, first.reason, first.points, first.excused) == ("17.08.2026", "Arzt", 3, None)
    assert [(r.time, r.course) for r in first.reports] == [("13:30 bis 14:15", "fra-F.4.d"), ("14:25 bis 15:10", "fra-F.4.d")]
    assert (second.date_to, second.points, second.comment, second.reports) == ("26.08.2026", 0, "ok", [])
