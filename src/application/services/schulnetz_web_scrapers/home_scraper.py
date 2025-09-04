from bs4 import BeautifulSoup
from src.application.dtos.web.schulnetz_data_dto import SchulnetzDataDto
from src.application.dtos.web.absence_dto import AbsenceDto
from src.application.dtos.web.grade_dto import GradeDto
from src.application.dtos.web.event_dto import EventDto
from src.application.dtos.web.holiday_dto import HolidayDto

def scrape_home(html: str) -> SchulnetzDataDto:
    soup = BeautifulSoup(html, "html.parser")
    data = SchulnetzDataDto()

    # Holidays
    holidays_table = soup.find("h3", string="Ferienübersicht")
    if holidays_table:
        rows = holidays_table.find_next("table").find_all("tr")[1:]
        for row in rows:
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if cols:
                data.holidays.append(HolidayDto(name=cols[0], start=cols[1], end=cols[2]))

    # Events
    events_table = soup.find("h3", string="Termine")
    if events_table:
        rows = events_table.find_next("table").find_all("tr")[1:]
        for row in rows:
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if cols and "keine Elemente" not in cols[0]:
                data.events.append(EventDto(date=cols[0], time=cols[1], time_until=cols[2], location=cols[3], description=cols[4], info=cols[5]))

    # Grades
    grades_table = soup.find("h3", string="Ihre letzten Noten")
    if grades_table:
        rows = grades_table.find_next("table").find_all("tr")
        for row in rows:
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if cols:
                data.grades.append(GradeDto(course=cols[0], topic=cols[1], date=cols[2], grade=cols[3]))

    # Absences
    absences_table = soup.find("h3", string="Offene Absenzen")
    if absences_table:
        rows = absences_table.find_next("table").find_all("tr")[1:]
        for row in rows:
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if cols and "keine offenen Absenzen" not in cols[0]:
                data.open_absences.append(AbsenceDto(start=cols[0], end=cols[1], excuse_until=cols[2], status=cols[3]))

    # Company Info
    company_table = soup.find("h3", string="Angaben zum Lehrbetrieb")
    if company_table:
        rows = company_table.find_next("table").find_all("tr")
        for row in rows:
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cols) == 2:
                if cols[0] == "Name": data.company_info.name = cols[1]
                elif cols[0] == "Strasse": data.company_info.street = cols[1]
                elif cols[0] == "PLZ Ort": data.company_info.postal_city = cols[1]
                elif cols[0] == "AusbildnerIn": data.company_info.trainer = cols[1]
                elif cols[0] == "Telefon Betrieb": data.company_info.phone = cols[1]
                elif cols[0] == "E-Mail Betrieb": data.company_info.email = cols[1]

    # Personal Info
    personal_table = soup.find("h3", string="Persönliche Angaben")
    if personal_table:
        rows = personal_table.find_next("table").find_all("tr")
        for row in rows:
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cols) == 2:
                if cols[0] == "Name Vorname": data.personal_info.full_name = cols[1]
                elif cols[0] == "Strasse": data.personal_info.street = cols[1]
                elif cols[0] == "PLZ Ort": data.personal_info.postal_city = cols[1]
                elif cols[0] == "Geburtsdatum": data.personal_info.birthdate = cols[1]
                elif cols[0] == "Ausbildung": data.personal_info.education = cols[1]
                elif cols[0] == "LV Nummer": data.personal_info.contract_number = cols[1]
                elif cols[0] == "Heimatort": data.personal_info.hometown = cols[1]
                elif cols[0] == "Telefon": data.personal_info.phone = cols[1]
                elif cols[0] == "Mobiltelefon": data.personal_info.mobile_phone = cols[1]

    return data
