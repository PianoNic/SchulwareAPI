from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from mediatorx import Mediator

from src.api.auth.bearer import security
from src.api.auth.token_dependency import get_current_token
from src.api.controller import controller
from src.api.dependencies import get_mediator, get_schulnetz_base_url
from src.application.dtos.mobile.absence_dto import AbsenceDto
from src.application.dtos.mobile.absencenotice_dto import AbsenceNoticeDto
from src.application.dtos.mobile.absencenoticestatus_dto import AbsenceNoticeStatusDto
from src.application.dtos.mobile.event_dto import EventDto
from src.application.dtos.mobile.exam_dto import ExamDto
from src.application.dtos.mobile.grade_dto import GradeDto
from src.application.dtos.mobile.homework_dto import HomeworkDto, ObjectiveDto
from src.application.dtos.mobile.lateness_dto import LatenessDto
from src.application.dtos.mobile.notification_dto import NotificationDto
from src.application.dtos.mobile.setting_dto import SettingDto
from src.application.dtos.mobile.student_id_card_dto import StudentIdCardDto
from src.application.dtos.mobile.topic_dto import TopicDto
from src.application.dtos.mobile.user_info_dto import UserInfoDto
from src.application.dtos.mobile.vacation_dto import VacationDto
from src.application.queries.proxy_mobile_rest_query import ProxyMobileRestQuery

router = APIRouter(prefix="/api/mobile", tags=["Mobile Proxy"])

@controller(router)
class MobileProxyController:
    mediator: Mediator = Depends(get_mediator)

    # === User Info ===

    @router.get("/userInfo", dependencies=[Depends(security)], response_model=UserInfoDto)
    async def get_user_info(self, token: str = Depends(get_current_token), base_url: str = Depends(get_schulnetz_base_url)):
        return await self.mediator.send(ProxyMobileRestQuery(token, "me", "GET", base_url=base_url))

    # === Grades ===

    @router.get("/grades", dependencies=[Depends(security)], response_model=list[GradeDto])
    async def get_grades(self, token: str = Depends(get_current_token), base_url: str = Depends(get_schulnetz_base_url)):
        return await self.mediator.send(ProxyMobileRestQuery(token, "me/grades", "GET", base_url=base_url))

    # === Events / Timetable ===

    @router.get("/events", dependencies=[Depends(security)], response_model=list[EventDto])
    async def get_events(
        self,
        token: str = Depends(get_current_token),
        base_url: str = Depends(get_schulnetz_base_url),
        min_date: str | None = Query(None),
        max_date: str | None = Query(None),
    ):
        query_params = [("min_date", min_date), ("max_date", max_date)]
        return await self.mediator.send(ProxyMobileRestQuery(token, "me/events", "GET", base_url=base_url, query_params=query_params))

    @router.get("/agenda", dependencies=[Depends(security)], response_model=list[EventDto])
    async def get_agenda(
        self,
        token: str = Depends(get_current_token),
        base_url: str = Depends(get_schulnetz_base_url),
        min_date: str | None = Query(None),
        max_date: str | None = Query(None),
    ):
        query_params = [("min_date", min_date), ("max_date", max_date)]
        return await self.mediator.send(ProxyMobileRestQuery(token, "me/events", "GET", base_url=base_url, query_params=query_params))

    # === Exams ===

    @router.get("/exams", dependencies=[Depends(security)], response_model=list[ExamDto])
    async def get_exams(self, token: str = Depends(get_current_token), base_url: str = Depends(get_schulnetz_base_url)):
        return await self.mediator.send(ProxyMobileRestQuery(token, "me/exams", "GET", base_url=base_url))

    # === Absences ===

    @router.get("/absences", dependencies=[Depends(security)], response_model=list[AbsenceDto])
    async def get_absences(self, token: str = Depends(get_current_token), base_url: str = Depends(get_schulnetz_base_url)):
        return await self.mediator.send(ProxyMobileRestQuery(token, "me/absences", "GET", base_url=base_url))

    @router.get("/absencenotices", dependencies=[Depends(security)], response_model=list[AbsenceNoticeDto])
    async def get_absence_notices(self, token: str = Depends(get_current_token), base_url: str = Depends(get_schulnetz_base_url)):
        return await self.mediator.send(ProxyMobileRestQuery(token, "me/absencenotices", "GET", base_url=base_url))

    @router.get("/absencenoticestatus", dependencies=[Depends(security)], response_model=list[AbsenceNoticeStatusDto])
    async def get_absence_notice_status(self, token: str = Depends(get_current_token), base_url: str = Depends(get_schulnetz_base_url)):
        return await self.mediator.send(ProxyMobileRestQuery(token, "config/lists/absenceNoticeStatus", "GET", base_url=base_url))

    @router.get("/absences/confirmed", dependencies=[Depends(security)])
    async def get_absences_confirmed(self, token: str = Depends(get_current_token), base_url: str = Depends(get_schulnetz_base_url)):
        return await self.mediator.send(ProxyMobileRestQuery(token, "me/absencesAndLateness/isAlreadyConfirmed", "GET", base_url=base_url))

    # === Lateness ===

    @router.get("/lateness", dependencies=[Depends(security)], response_model=list[LatenessDto])
    async def get_lateness(self, token: str = Depends(get_current_token), base_url: str = Depends(get_schulnetz_base_url)):
        return await self.mediator.send(ProxyMobileRestQuery(token, "me/lateness", "GET", base_url=base_url))

    # === Vacations ===

    @router.get("/vacations", dependencies=[Depends(security)], response_model=list[VacationDto])
    async def get_vacations(self, token: str = Depends(get_current_token), base_url: str = Depends(get_schulnetz_base_url)):
        return await self.mediator.send(ProxyMobileRestQuery(token, "me/vacations", "GET", base_url=base_url))

    # === Notes ===

    @router.get("/homework", dependencies=[Depends(security)], response_model=list[HomeworkDto])
    async def get_homework(self, token: str = Depends(get_current_token), base_url: str = Depends(get_schulnetz_base_url)):
        return await self.mediator.send(ProxyMobileRestQuery(token, "me/notes/homework", "GET", base_url=base_url))

    @router.get("/objectives", dependencies=[Depends(security)], response_model=list[ObjectiveDto])
    async def get_objectives(self, token: str = Depends(get_current_token), base_url: str = Depends(get_schulnetz_base_url)):
        return await self.mediator.send(ProxyMobileRestQuery(token, "me/notes/objectives", "GET", base_url=base_url))

    # === Notifications ===

    @router.get("/notifications", dependencies=[Depends(security)], response_model=list[NotificationDto])
    async def get_notifications(self, token: str = Depends(get_current_token), base_url: str = Depends(get_schulnetz_base_url)):
        return await self.mediator.send(ProxyMobileRestQuery(token, "me/notifications/push", "GET", base_url=base_url))

    @router.get("/topics", dependencies=[Depends(security)], response_model=list[TopicDto])
    async def get_topics(self, token: str = Depends(get_current_token), base_url: str = Depends(get_schulnetz_base_url)):
        return await self.mediator.send(ProxyMobileRestQuery(token, "me/notifications/topics", "GET", base_url=base_url))

    # === Config ===

    @router.get("/settings", dependencies=[Depends(security)], response_model=list[SettingDto])
    async def get_settings(self, token: str = Depends(get_current_token), base_url: str = Depends(get_schulnetz_base_url)):
        return await self.mediator.send(ProxyMobileRestQuery(token, "config/settings", "GET", base_url=base_url))

    @router.get("/customfields", dependencies=[Depends(security)])
    async def get_custom_fields(self, token: str = Depends(get_current_token), base_url: str = Depends(get_schulnetz_base_url)):
        return await self.mediator.send(ProxyMobileRestQuery(token, "config/customFields", "GET", base_url=base_url))

    @router.get("/filecategories", dependencies=[Depends(security)])
    async def get_file_categories(self, token: str = Depends(get_current_token), base_url: str = Depends(get_schulnetz_base_url)):
        return await self.mediator.send(ProxyMobileRestQuery(token, "config/filestoreCategories", "GET", base_url=base_url))

    # === Student ID Card ===

    @router.get("/studentidcard/{report_id}", dependencies=[Depends(security)], response_model=StudentIdCardDto)
    async def get_student_id_card(self, report_id: int, token: str = Depends(get_current_token), base_url: str = Depends(get_schulnetz_base_url)):
        response = await self.mediator.send(ProxyMobileRestQuery(token, f"me/cockpitReport/{report_id}", "GET", base_url=base_url))
        html_content = response.body.decode("utf-8")
        if html_content.startswith('"') and html_content.endswith('"'):
            html_content = html_content[1:-1]
        html_content = html_content.replace('\\r\\n', '').replace('\\r', '').replace('\\n', '')
        html_content = html_content.replace('\\"', '"')
        return StudentIdCardDto(html=html_content)
