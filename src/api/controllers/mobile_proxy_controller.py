from fastapi import Query, Depends
from typing import List, Optional
from src.application.dtos.mobile.student_id_card_dto import StudentIdCardDto
from src.application.dtos.mobile.lateness_dto import LatenessDto
from src.application.dtos.mobile.topic_dto import TopicDto
from src.application.dtos.mobile.notification_dto import NotificationDto
from src.application.dtos.mobile.grade_dto import GradeDto
from src.application.dtos.mobile.exam_dto import ExamDto
from src.application.dtos.mobile.absencenotice_dto import AbsenceNoticeDto
from src.application.dtos.mobile.absencenoticestatus_dto import AbsenceNoticeStatusDto
from src.application.dtos.mobile.absence_dto import AbsenceDto
from src.application.dtos.mobile.agenda_dto import AgendaDto
from src.application.dtos.mobile.setting_dto import SettingDto
from src.application.dtos.mobile.user_info_dto import UserInfoDto
from src.application.queries.proxy_mobile_rest_query import proxy_mobile_rest_query_async
from src.api.auth.token_dependency import get_current_token
from src.api.auth.bearer import security
from src.api.router_registry import SchulwareAPIRouter

router = SchulwareAPIRouter()

@router.get("userInfo", dependencies=[Depends(security)], response_model=UserInfoDto)
async def get_mobile_user_info(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me", "GET")

@router.get("settings", dependencies=[Depends(security)], response_model=List[SettingDto])
async def get_mobile_settings(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "config/settings", "GET")

@router.get("agenda", dependencies=[Depends(security)], response_model=List[AgendaDto])
async def get_mobile_events(token: str = Depends(get_current_token), min_date: Optional[str] = Query(None), max_date: Optional[str] = Query(None)):
    query_params = [("min_date", min_date), ("max_date", max_date)]
    return await proxy_mobile_rest_query_async(token, "me/events", "GET", query_params=query_params)

@router.get("absences", dependencies=[Depends(security)], response_model=List[AbsenceDto])
async def get_mobile_absences(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/absences", "GET")

@router.get("absencenotices", dependencies=[Depends(security)], response_model=List[AbsenceNoticeDto])
async def get_mobile_absence_notices(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/absencenotices", "GET")

@router.get("absencenoticestatus", dependencies=[Depends(security)], response_model=List[AbsenceNoticeStatusDto])
async def get_mobile_absence_notice_status( token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "config/lists/absenceNoticeStatus", "GET")

@router.get("exams", dependencies=[Depends(security)], response_model=List[ExamDto])
async def get_mobile_exams(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/exams", "GET")

@router.get("grades", dependencies=[Depends(security)], response_model=List[GradeDto])
async def get_mobile_grades(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/grades", "GET")

@router.get("notifications", dependencies=[Depends(security)], response_model=List[NotificationDto])
async def get_mobile_notifications(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/notifications/push", "GET")

@router.get("topics", dependencies=[Depends(security)], response_model=List[TopicDto])
async def get_mobile_topics(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/notifications/topics", "GET")

@router.get("lateness", dependencies=[Depends(security)], response_model=List[LatenessDto])
async def get_mobile_lateness(token: str = Depends(get_current_token)):
    return await proxy_mobile_rest_query_async(token, "me/lateness", "GET")

@router.get("studentidcard/{report_id}", dependencies=[Depends(security)], response_model=StudentIdCardDto)
async def get_mobile_cockpit_report(report_id: int, token: str = Depends(get_current_token)):
    response = await proxy_mobile_rest_query_async(token, f"me/cockpitReport/{report_id}", "GET")
    html_content = response.body.decode("utf-8")
    if html_content.startswith('"') and html_content.endswith('"'):
        html_content = html_content[1:-1]
    html_content = html_content.encode('utf-8').decode('unicode_escape')
    return StudentIdCardDto(html=html_content)