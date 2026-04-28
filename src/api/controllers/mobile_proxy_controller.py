from __future__ import annotations
from typing import Optional
from fastapi import Query, Depends
from src.application.dtos.mobile.student_id_card_dto import StudentIdCardDto
from src.application.dtos.mobile.lateness_dto import LatenessDto
from src.application.dtos.mobile.topic_dto import TopicDto
from src.application.dtos.mobile.notification_dto import NotificationDto
from src.application.dtos.mobile.grade_dto import GradeDto
from src.application.dtos.mobile.exam_dto import ExamDto
from src.application.dtos.mobile.event_dto import EventDto
from src.application.dtos.mobile.absence_dto import AbsenceDto
from src.application.dtos.mobile.absencenotice_dto import AbsenceNoticeDto
from src.application.dtos.mobile.absencenoticestatus_dto import AbsenceNoticeStatusDto
from src.application.dtos.mobile.setting_dto import SettingDto
from src.application.dtos.mobile.user_info_dto import UserInfoDto
from src.application.dtos.mobile.vacation_dto import VacationDto
from src.application.dtos.mobile.homework_dto import HomeworkDto, ObjectiveDto
from src.application.queries.proxy_mobile_rest_query import proxy_mobile_rest_query_async
from src.api.auth.token_dependency import get_current_token
from src.api.auth.bearer import security
from src.api.router_registry import SchulwareAPIRouter

router = SchulwareAPIRouter()


# === User Info ===

@router.get("userInfo", dependencies=[Depends(security)], response_model=UserInfoDto)
async def get_user_info(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me", "GET")


# === Grades ===

@router.get("grades", dependencies=[Depends(security)], response_model=list[GradeDto])
async def get_grades(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/grades", "GET")


# === Events / Timetable ===

@router.get("events", dependencies=[Depends(security)], response_model=list[EventDto])
async def get_events(
    token: str = Depends(get_current_token),
    min_date: Optional[str] = Query(None),
    max_date: Optional[str] = Query(None),
):
    query_params = [("min_date", min_date), ("max_date", max_date)]
    return await proxy_mobile_rest_query_async(token, "me/events", "GET", query_params=query_params)

@router.get("agenda", dependencies=[Depends(security)], response_model=list[EventDto])
async def get_agenda(
    token: str = Depends(get_current_token),
    min_date: Optional[str] = Query(None),
    max_date: Optional[str] = Query(None),
):
    query_params = [("min_date", min_date), ("max_date", max_date)]
    return await proxy_mobile_rest_query_async(token, "me/events", "GET", query_params=query_params)


# === Exams ===

@router.get("exams", dependencies=[Depends(security)], response_model=list[ExamDto])
async def get_exams(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/exams", "GET")


# === Absences ===

@router.get("absences", dependencies=[Depends(security)], response_model=list[AbsenceDto])
async def get_absences(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/absences", "GET")

@router.get("absencenotices", dependencies=[Depends(security)], response_model=list[AbsenceNoticeDto])
async def get_absence_notices(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/absencenotices", "GET")

@router.get("absencenoticestatus", dependencies=[Depends(security)], response_model=list[AbsenceNoticeStatusDto])
async def get_absence_notice_status(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "config/lists/absenceNoticeStatus", "GET")

@router.get("absences/confirmed", dependencies=[Depends(security)])
async def get_absences_confirmed(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/absencesAndLateness/isAlreadyConfirmed", "GET")


# === Lateness ===

@router.get("lateness", dependencies=[Depends(security)], response_model=list[LatenessDto])
async def get_lateness(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/lateness", "GET")


# === Vacations ===

@router.get("vacations", dependencies=[Depends(security)], response_model=list[VacationDto])
async def get_vacations(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/vacations", "GET")


# === Notes ===

@router.get("homework", dependencies=[Depends(security)], response_model=list[HomeworkDto])
async def get_homework(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/notes/homework", "GET")

@router.get("objectives", dependencies=[Depends(security)], response_model=list[ObjectiveDto])
async def get_objectives(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/notes/objectives", "GET")


# === Notifications ===

@router.get("notifications", dependencies=[Depends(security)], response_model=list[NotificationDto])
async def get_notifications(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/notifications/push", "GET")

@router.get("topics", dependencies=[Depends(security)], response_model=list[TopicDto])
async def get_topics(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/notifications/topics", "GET")


# === Config ===

@router.get("settings", dependencies=[Depends(security)], response_model=list[SettingDto])
async def get_settings(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "config/settings", "GET")

@router.get("customfields", dependencies=[Depends(security)])
async def get_custom_fields(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "config/customFields", "GET")

@router.get("filecategories", dependencies=[Depends(security)])
async def get_file_categories(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "config/filestoreCategories", "GET")


# === Student ID Card ===

@router.get("studentidcard/{report_id}", dependencies=[Depends(security)], response_model=StudentIdCardDto)
async def get_student_id_card(report_id: int, token: str = Depends(get_current_token)):
    response = await proxy_mobile_rest_query_async(token, f"me/cockpitReport/{report_id}", "GET")
    html_content = response.body.decode("utf-8")
    if html_content.startswith('"') and html_content.endswith('"'):
        html_content = html_content[1:-1]
    html_content = html_content.replace('\\r\\n', '').replace('\\r', '').replace('\\n', '')
    html_content = html_content.replace('\\"', '"')
    return StudentIdCardDto(html=html_content)
