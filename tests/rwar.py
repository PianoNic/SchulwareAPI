#https://claude.ai/chat/f211177f-a2bb-452f-8696-61f6ae798675

import httpx
from bs4 import BeautifulSoup
from datetime import datetime, time
from enum import Enum

class AbsenceReason(Enum):
    ILLNESS = "1"
    ACCIDENT = "2"
    MILITARY = "3"
    MEDICAL_CERTIFICATE = "4"
    OTHER = "5"

class AbsenceType(Enum):
    RELEVANT = "0"

class Student(Enum):
    DEFAULT = "0"

async def get_form_tokens(session_id: str, base_url: str):
    url = f"{base_url}/index.php?pageid=21119&action=new&tblName=tblAbsenzen"
    
    async with httpx.AsyncClient(
        cookies={"PHPSESSID": session_id},
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        varsize_input = soup.find("input", {"name": "varsize"})
        if not varsize_input:
            raise ValueError("Varsize token not found")
        
        form = soup.find("form", {"name": "standardformular"})
        if not form:
            raise ValueError("Form not found")
        
        form_action = form.get("action", "").replace("&amp;", "&")
        
        return varsize_input["value"], form_action


async def submit_absence(
    session_id: str,
    start_date: datetime,
    end_date: datetime,
    reason: AbsenceReason,
    start_time: time = None,
    end_time: time = None,
    comment: str = "",
    student: Student = Student.DEFAULT,
    absence_type: AbsenceType = AbsenceType.RELEVANT
) -> httpx.Response:
    
    base_url = "https://schulnetz.bbbaden.ch"
    varsize, form_action = await get_form_tokens(session_id, "https://schulnetz.bbbaden.ch")
    
    url = f"{base_url}/{form_action}"
    
    data = {
        "f0": student.value,
        "f1": reason.value,
        "f2": absence_type.value,
        "f3": start_date.strftime("%d.%m.%Y"),
        "f4": end_date.strftime("%d.%m.%Y"),
        "f5": start_time.strftime("%H:%M") if start_time else "",
        "f6": end_time.strftime("%H:%M") if end_time else "",
        "f7": comment,
        "listindex": "",
        "varsize": varsize,
        "timeeditdate": "",
        "timeeditdatedeletion": "",
        "timeeditcomment": ""
    }
    
    headers = {
        "Origin": base_url,
        "Referer": f"{base_url}/index.php?pageid=21119&action=new&tblName=tblAbsenzen",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    async with httpx.AsyncClient(
        cookies={"PHPSESSID": session_id},
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    ) as client:
        response = await client.post(url, data=data, headers=headers)
        return response


async def main():
    response = await submit_absence(
        session_id="your_session_id",
        start_date=datetime(2025, 11, 5),
        end_date=datetime(2025, 11, 5),
        reason=AbsenceReason.OTHER,
        start_time=time(8, 20),
        end_time=time(17, 30),
        comment="Teilnahme ICT Swiss Skills"
    )
    
    print(f"Status: {response.status_code}")
    print("Success!" if response.status_code == 200 else "Failed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())