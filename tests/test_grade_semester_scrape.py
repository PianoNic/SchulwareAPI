"""Regression: the grade scrape must cover semesters NEWER than the session's
selected one. A session captured in an earlier term stays pinned there, so the
current term (with the student's newest grades) sits above the selected option
in the newest-first dropdown and must still be scraped."""

import pytest

from src.application.queries import scrape_web_page_query as q
from src.application.dtos.web.scrape_dtos import CourseGradesDto, GradesPageDto


@pytest.mark.asyncio
async def test_scrapes_semesters_newer_than_the_selected_one(monkeypatch):
    # Newest-first dropdown: a future placeholder (empty), the CURRENT term with
    # the new grades (NOT selected), the session-pinned OLD term, then history.
    options = [
        ("99", "2. 35/36", False),  # future placeholder — empty
        ("41", "2. 25/26", False),  # current term, has the NEW grades, not selected
        ("40", "1. 25/26", True),   # session is pinned to this older term
        ("39", "2. 24/25", False),  # older — empty
        ("38", "1. 24/25", False),  # older — empty (2nd in a row → stop)
    ]
    data_by_sem = {
        "41": [CourseGradesDto(course="Math new", course_token="M", average=5.0, confirmed=False, exams=[])],
        "40": [CourseGradesDto(course="Math old", course_token="M", average=4.0, confirmed=False, exams=[])],
    }
    state = {"sem": "40"}  # the session starts on the old term

    async def fake_save_semid(base, cookies, sid, transid, sem_id, user_agent=None):
        state["sem"] = sem_id
        return True

    async def fake_scrape_page(base, cookies, pageid, sid, transid, user_agent=None):
        return f"<html data-sem='{state['sem']}'></html>"

    def fake_scrape_noten(html):
        return GradesPageDto(student="Stud", courses=data_by_sem.get(state["sem"], []))

    monkeypatch.setattr(q, "parse_semester_options", lambda html: options)
    monkeypatch.setattr(q, "save_semid", fake_save_semid)
    monkeypatch.setattr(q, "scrape_page", fake_scrape_page)
    monkeypatch.setattr(q, "scrape_noten", fake_scrape_noten)

    result = await q._scrape_all_semester_grades("http://x", {}, "sid", "tid", "ua")
    names = {c.course for c in result.courses}

    assert "Math new" in names, "current-term grades (newer than selected) were missed"
    assert "Math old" in names
    assert state["sem"] == "40", "session must be restored to its original semester"
