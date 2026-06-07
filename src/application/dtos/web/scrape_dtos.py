"""Typed response models for the Schulnetz web-scraper endpoints.

Each Schulnetz page maps to a domain model here. The scrapers in
`schulnetz_web_scrapers/` parse the page HTML into these, so `/api/websession/scrape`
returns typed objects (and the generated clients get real types) instead of a
freeform `dict[str, Any]`.
"""

from pydantic import BaseModel


# --- Grades (Noten, pageid 21311) -------------------------------------------

class ExamGradeDto(BaseModel):
    date: str | None = None          # "04.03.2026"
    topic: str | None = None         # "Geschichte: Imperialismus"
    mark: float | None = None        # 5.5
    points: float | None = None      # 23.5 (from "Punkte: 23.5"), when present
    weight: float | None = None      # 1
    class_average: float | None = None  # Klassenschnitt, when shown


class CourseGradesDto(BaseModel):
    course: str | None = None        # human-readable name, e.g. "Geschichte und Politik"
    course_token: str | None = None  # course code, e.g. "GP-BM23d-ArAr" (matches the timetable's kurskuerzel)
    average: float | None = None     # 5.500 (Notendurchschnitt)
    confirmed: bool | None = None    # Bestätigt
    exams: list[ExamGradeDto] = []


class GradesPageDto(BaseModel):
    student: str | None = None       # from the page heading
    courses: list[CourseGradesDto] = []


# --- Absences (Absenzen, pageid 21111) --------------------------------------

class AbsenceReportDto(BaseModel):
    date: str | None = None          # Datum
    time: str | None = None          # Zeit ("07:30 bis 08:15")
    course: str | None = None        # Kurs / Kurskürzel
    remark: str | None = None        # Bemerkung


class WebAbsenceDto(BaseModel):
    date_from: str | None = None     # Datum von
    date_to: str | None = None       # Datum bis
    reason: str | None = None        # Grund
    additional_info: str | None = None   # Zusatzinfo
    extension_deadline: str | None = None  # Zusatzfrist
    status_eae: str | None = None    # Status EAE
    excused: bool | None = None      # Entschuldigt (Ja/Nein)
    lessons: int | None = None       # Lektionen
    comment: str | None = None       # Kommentar
    trainer_comment: str | None = None   # Kommentar ausbildende Person
    acknowledged_at: str | None = None   # Quittiert am
    reports: list[AbsenceReportDto] = []  # per-lesson Meldungen under this absence


class AbsencesPageDto(BaseModel):
    student: str | None = None
    absences: list[WebAbsenceDto] = []
    lesson_reports: list[AbsenceReportDto] = []  # standalone Datum/Zeit/Kurs/Bemerkung table


# --- Lessons (Unterricht, pageid 21355) -------------------------------------

class LessonDto(BaseModel):
    course: str | None = None        # Kurs
    title: str | None = None         # Titel
    description: str | None = None   # Beschreibung
    date: str | None = None          # Datum
    time: str | None = None          # Zeit
    overridden_amount: str | None = None  # Übersteuerter Betrag


class LessonsPageDto(BaseModel):
    lessons: list[LessonDto] = []


# --- Agenda / Schedule (pageid 21200, scheduler_processor.php XML) -----------

class ScheduleEventDto(BaseModel):
    id: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    text: str | None = None
    kommentar: str | None = None
    klasse: str | None = None
    zimmer: str | None = None
    zimmerkuerzel: str | None = None
    lehrerkuerzelname: str | None = None
    kurskuerzel: str | None = None
    kursid: str | None = None
    color: str | None = None
    event_type: str | None = None
    fachkuerzel: str | None = None
    wochentag: str | None = None
    lektionswert: str | None = None
    kalenderwoche: str | None = None
    schulanlage: str | None = None


class AgendaPageDto(BaseModel):
    events: list[ScheduleEventDto] = []


# --- Documents / files (Persönliches Dossier, pageid 10053) -----------------

class DocumentFileDto(BaseModel):
    title: str | None = None         # Titel
    comment: str | None = None       # Kommentar
    created_at: str | None = None    # Erfasst am
    created_by: str | None = None    # Erfasst von
    updated_at: str | None = None    # Aktualisiert am
    category: str | None = None      # Kategorie ("Zeugnis")
    filename: str | None = None      # Datei ("Zeugnis_IN23a.pdf")
    size: str | None = None          # Grösse ("865.85K")
    download_url: str | None = None  # absolute/relative URL to fetch the file


class DocumentsPageDto(BaseModel):
    files: list[DocumentFileDto] = []


# --- Student ID card (Ausweis, pageid 50505) --------------------------------

class WebStudentIdCardDto(BaseModel):
    # The card is absolutely-positioned base64 images + inline CSS; keep the raw
    # body so clients can render it faithfully.
    html: str | None = None


# --- Home / dashboard (pageid 1) --------------------------------------------
# The dashboard aggregates many heterogeneous sections (Ferienübersicht, Termine,
# letzte Noten, Direktlinks, offene Absenzen, Lehrbetrieb, persönliche Angaben),
# so it stays a generic-but-typed structure rather than one domain model.

class ScrapedTableDto(BaseModel):
    name: str | None = None          # nearest preceding heading
    columns: list[str] = []
    rows: list[dict[str, str]] = []


class ScrapedLinkDto(BaseModel):
    text: str | None = None
    href: str | None = None


class ScrapedImageDto(BaseModel):
    alt: str | None = None
    src: str | None = None


class HomePageDto(BaseModel):
    page_heading: str | None = None
    tables: list[ScrapedTableDto] = []
    key_value_blocks: dict[str, dict[str, str]] = {}
    links: list[ScrapedLinkDto] = []
    images: list[ScrapedImageDto] = []
