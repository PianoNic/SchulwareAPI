"""
Test Token Configuration and Mock Data

This module provides test/dummy bearer tokens and corresponding mock data
for testing API endpoints without making real API calls.

Test Token: "test-token-12345"
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Test Bearer Token - use in Authorization header as: Bearer test-token-12345
TEST_TOKEN = "test-token-12345"

def get_mock_user_info() -> Dict[str, Any]:
    """Generate mock user information matching UserInfoDto"""
    return {
        "id": "test-user-001",
        "userType": "student",
        "idNr": "12345678",
        "lastName": "User",
        "firstName": "Test",
        "loginActive": True,
        "gender": "M",
        "birthday": "2007-03-15",
        "street": "Teststrasse 123",
        "addressLine2": None,
        "postOfficeBox": None,
        "zip": "8000",
        "city": "Zurich",
        "nationality": "CH",
        "hometown": "Zurich",
        "phone": "+41441234567",
        "mobile": "+41791234567",
        "email": "test.user@school.ch",
        "emailPrivate": "test@example.com",
        "profil1": "Science",
        "profil2": "Mathematics",
        "entryDate": "2023-08-15",
        "exitDate": None,
        "regularClasses": [
            {
                "id": "class-001",
                "classId": "4a",
                "className": "4a",
                "schoolYear": "2024/2025"
            }
        ],
        "additionalClasses": []
    }

def get_mock_events(min_date: Optional[str] = None, max_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Generate mock calendar events matching AgendaDto"""
    today = datetime.now()

    events = [
        {
            "id": "agenda-001",
            "startDate": (today + timedelta(days=1, hours=8)).isoformat() + "Z",
            "endDate": (today + timedelta(days=1, hours=9)).isoformat() + "Z",
            "text": "Mathematics Lesson",
            "comment": "Chapter 5: Geometry",
            "roomToken": "R201",
            "roomId": "room-201",
            "teachers": ["Mr. Schmidt"],
            "teacherIds": ["teacher-001"],
            "teacherTokens": ["T001"],
            "courseId": "course-math-001",
            "courseToken": "MATH",
            "courseName": "Mathematics",
            "status": "confirmed",
            "color": "#4CAF50",
            "eventType": "lesson",
            "eventRoomStatus": "available",
            "timetableText": "Mathematics - Room 201",
            "infoFacilityManagement": None,
            "importset": "2024-2025",
            "lessons": "1-2",
            "publishToInfoSystem": "true",
            "studentNames": None,
            "studentIds": None,
            "client": "schulnetz",
            "clientname": "SchulNetz",
            "weight": "1.0"
        },
        {
            "id": "agenda-002",
            "startDate": (today + timedelta(days=2, hours=10)).isoformat() + "Z",
            "endDate": (today + timedelta(days=2, hours=11, minutes=30)).isoformat() + "Z",
            "text": "English Class",
            "comment": "Shakespeare's Hamlet Analysis",
            "roomToken": "R105",
            "roomId": "room-105",
            "teachers": ["Mrs. Johnson"],
            "teacherIds": ["teacher-002"],
            "teacherTokens": ["T002"],
            "courseId": "course-eng-001",
            "courseToken": "ENG",
            "courseName": "English",
            "status": "confirmed",
            "color": "#2196F3",
            "eventType": "lesson",
            "eventRoomStatus": "available",
            "timetableText": "English - Room 105",
            "infoFacilityManagement": None,
            "importset": "2024-2025",
            "lessons": "3-4",
            "publishToInfoSystem": "true",
            "studentNames": None,
            "studentIds": None,
            "client": "schulnetz",
            "clientname": "SchulNetz",
            "weight": "1.0"
        }
    ]

    return events

def get_mock_grades() -> List[Dict[str, Any]]:
    """Generate mock student grades matching GradeDto"""
    return [
        {
            "id": "grade-001",
            "course": "Mathematics 4a",
            "courseId": "course-math-001",
            "courseType": "regular",
            "subject": "Mathematics",
            "subjectToken": "MATH",
            "title": "Chapter 4 Test",
            "date": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
            "mark": "5.5",
            "points": "27.5",
            "weight": "1.0",
            "isConfirmed": True,
            "courseGrade": "5.3",
            "examinationGroups": None,
            "studentId": "test-user-001",
            "studentName": "Test User",
            "inputType": "exam",
            "comment": "Good progress"
        },
        {
            "id": "grade-002",
            "course": "English 4a",
            "courseId": "course-eng-001",
            "courseType": "regular",
            "subject": "English",
            "subjectToken": "ENG",
            "title": "Hamlet Essay",
            "date": (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d"),
            "mark": "4.75",
            "points": "23.75",
            "weight": "1.0",
            "isConfirmed": True,
            "courseGrade": "4.8",
            "examinationGroups": None,
            "studentId": "test-user-001",
            "studentName": "Test User",
            "inputType": "written",
            "comment": "Well structured argument"
        },
        {
            "id": "grade-003",
            "course": "Physics 4a",
            "courseId": "course-phys-001",
            "courseType": "regular",
            "subject": "Physics",
            "subjectToken": "PHYS",
            "title": "Lab Report",
            "date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
            "mark": "5.25",
            "points": "26.25",
            "weight": "1.5",
            "isConfirmed": True,
            "courseGrade": "5.1",
            "examinationGroups": None,
            "studentId": "test-user-001",
            "studentName": "Test User",
            "inputType": "practical",
            "comment": "Excellent experimental technique"
        }
    ]

def get_mock_absences() -> List[Dict[str, Any]]:
    """Generate mock absence data matching AbsenceDto"""
    return [
        {
            "id": "absence-001",
            "studentId": "test-user-001",
            "dateFrom": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "dateTo": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "hourFrom": "08:00",
            "hourTo": "08:45",
            "subject": "French",
            "subjectId": "subj-fr-001",
            "profile": "Regular",
            "profileId": "profile-001",
            "lessons": "1",
            "reason": "Doctor's appointment",
            "category": "medical",
            "comment": "Medical certificate provided",
            "remark": None,
            "isAcknowledged": True,
            "isExcused": True,
            "excusedDate": (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d"),
            "additionalPeriod": 0,
            "statusEAE": "confirmed",
            "dateEAE": (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d"),
            "statusEAB": "excused",
            "dateEAB": (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d"),
            "commentEAB": "Excused due to medical appointment",
            "studentTimestamp": (datetime.now() - timedelta(days=30)).isoformat() + "Z"
        },
        {
            "id": "absence-002",
            "studentId": "test-user-001",
            "dateFrom": (datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d"),
            "dateTo": (datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d"),
            "hourFrom": "10:00",
            "hourTo": "11:30",
            "subject": "Physical Education",
            "subjectId": "subj-pe-001",
            "profile": "Regular",
            "profileId": "profile-001",
            "lessons": "3-4",
            "reason": "Sports injury",
            "category": "injury",
            "comment": "Ankle sprain",
            "remark": None,
            "isAcknowledged": True,
            "isExcused": True,
            "excusedDate": (datetime.now() - timedelta(days=19)).strftime("%Y-%m-%d"),
            "additionalPeriod": 0,
            "statusEAE": "confirmed",
            "dateEAE": (datetime.now() - timedelta(days=19)).strftime("%Y-%m-%d"),
            "statusEAB": "excused",
            "dateEAB": (datetime.now() - timedelta(days=19)).strftime("%Y-%m-%d"),
            "commentEAB": "Excused due to sports injury",
            "studentTimestamp": (datetime.now() - timedelta(days=20)).isoformat() + "Z"
        },
        {
            "id": "absence-003",
            "studentId": "test-user-001",
            "dateFrom": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
            "dateTo": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
            "hourFrom": "08:00",
            "hourTo": "08:30",
            "subject": "History",
            "subjectId": "subj-hist-001",
            "profile": "Regular",
            "profileId": "profile-001",
            "lessons": "1",
            "reason": "Late arrival",
            "category": "unexcused",
            "comment": "No excuse provided",
            "remark": "Student arrived 30 minutes late",
            "isAcknowledged": False,
            "isExcused": False,
            "excusedDate": None,
            "additionalPeriod": 0,
            "statusEAE": "pending",
            "dateEAE": None,
            "statusEAB": "pending",
            "dateEAB": None,
            "commentEAB": None,
            "studentTimestamp": (datetime.now() - timedelta(days=10)).isoformat() + "Z"
        }
    ]

def get_mock_timetable() -> List[Dict[str, Any]]:
    """Generate mock weekly timetable using AgendaDto structure"""
    today = datetime.now()
    # Generate a week of timetable entries
    timetable = []
    
    # Monday
    timetable.append({
        "id": "timetable-mon-1",
        "startDate": (today + timedelta(days=(0 - today.weekday()), hours=8)).isoformat() + "Z",
        "endDate": (today + timedelta(days=(0 - today.weekday()), hours=8, minutes=45)).isoformat() + "Z",
        "text": "Mathematics",
        "comment": "Algebra and Geometry",
        "roomToken": "R201",
        "roomId": "room-201",
        "teachers": ["Mr. Schmidt"],
        "teacherIds": ["teacher-001"],
        "teacherTokens": ["T001"],
        "courseId": "course-math-001",
        "courseToken": "MATH",
        "courseName": "Mathematics",
        "status": "confirmed",
        "color": "#4CAF50",
        "eventType": "lesson",
        "eventRoomStatus": "available",
        "timetableText": "Mathematics - Room 201",
        "infoFacilityManagement": None,
        "importset": "2024-2025",
        "lessons": "1",
        "publishToInfoSystem": "true",
        "studentNames": None,
        "studentIds": None,
        "client": "schulnetz",
        "clientname": "SchulNetz",
        "weight": "1.0"
    })
    
    # Tuesday
    timetable.append({
        "id": "timetable-tue-1",
        "startDate": (today + timedelta(days=(1 - today.weekday()), hours=10)).isoformat() + "Z",
        "endDate": (today + timedelta(days=(1 - today.weekday()), hours=11, minutes=30)).isoformat() + "Z",
        "text": "English",
        "comment": "Literature Analysis",
        "roomToken": "R105",
        "roomId": "room-105",
        "teachers": ["Mrs. Johnson"],
        "teacherIds": ["teacher-002"],
        "teacherTokens": ["T002"],
        "courseId": "course-eng-001",
        "courseToken": "ENG",
        "courseName": "English",
        "status": "confirmed",
        "color": "#2196F3",
        "eventType": "lesson",
        "eventRoomStatus": "available",
        "timetableText": "English - Room 105",
        "infoFacilityManagement": None,
        "importset": "2024-2025",
        "lessons": "3",
        "publishToInfoSystem": "true",
        "studentNames": None,
        "studentIds": None,
        "client": "schulnetz",
        "clientname": "SchulNetz",
        "weight": "1.0"
    })
    
    return timetable

def get_mock_documents() -> List[Dict[str, Any]]:
    """Generate mock documents list - returns flexible structure (no specific DTO)"""
    return [
        {
            "id": "doc-001",
            "name": "Mathematics_Chapter5.pdf",
            "subject": "Mathematics",
            "type": "lecture_notes",
            "uploaded_by": "Mr. Schmidt",
            "date": (datetime.now() - timedelta(days=3)).isoformat() + "Z",
            "size_bytes": 2048576,
            "download_url": "/api/documents/doc-001/download"
        },
        {
            "id": "doc-002",
            "name": "Hamlet_Study_Guide.docx",
            "subject": "English",
            "type": "study_material",
            "uploaded_by": "Mrs. Johnson",
            "date": (datetime.now() - timedelta(days=7)).isoformat() + "Z",
            "size_bytes": 524288,
            "download_url": "/api/documents/doc-002/download"
        },
        {
            "id": "doc-003",
            "name": "Physics_Lab_Report_Template.pdf",
            "subject": "Physics",
            "type": "template",
            "uploaded_by": "Dr. Mueller",
            "date": (datetime.now() - timedelta(days=1)).isoformat() + "Z",
            "size_bytes": 1048576,
            "download_url": "/api/documents/doc-003/download"
        }
    ]

def get_mock_settings() -> List[Dict[str, Any]]:
    """Generate mock application settings matching SettingDto"""
    return [
        {
            "key": "notifications_enabled",
            "value": "true"
        },
        {
            "key": "email_notifications",
            "value": "true"
        },
        {
            "key": "theme",
            "value": "light"
        },
        {
            "key": "language",
            "value": "de"
        },
        {
            "key": "auto_sync",
            "value": "true"
        }
    ]

def get_mock_exams() -> List[Dict[str, Any]]:
    """Generate mock exam schedule matching ExamDto"""
    return [
        {
            "id": "exam-001",
            "startDate": (datetime.now() + timedelta(days=14, hours=9)).isoformat() + "Z",
            "endDate": (datetime.now() + timedelta(days=14, hours=11)).isoformat() + "Z",
            "text": "Final Mathematics Exam",
            "comment": "Comprehensive exam covering chapters 1-5",
            "roomToken": "R201",
            "roomId": "room-201",
            "teachers": ["Mr. Schmidt"],
            "teacherIds": ["teacher-001"],
            "teacherTokens": ["T001"],
            "courseId": "course-math-001",
            "courseToken": "MATH",
            "courseName": "Mathematics",
            "status": "confirmed",
            "color": "#FF5722",
            "eventType": "exam",
            "eventRoomStatus": "reserved",
            "timetableText": "Mathematics Final Exam",
            "infoFacilityManagement": None,
            "importset": "2024-2025",
            "lessons": ["1", "2", "3", "4"],
            "publishToInfoSystem": True,
            "studentNames": ["Test User"],
            "studentIds": ["test-user-001"],
            "client": "schulnetz",
            "clientname": "SchulNetz",
            "weight": "2.0"
        },
        {
            "id": "exam-002",
            "startDate": (datetime.now() + timedelta(days=16, hours=10)).isoformat() + "Z",
            "endDate": (datetime.now() + timedelta(days=16, hours=12)).isoformat() + "Z",
            "text": "English Language Exam",
            "comment": "Written and oral examination",
            "roomToken": "R105",
            "roomId": "room-105",
            "teachers": ["Mrs. Johnson"],
            "teacherIds": ["teacher-002"],
            "teacherTokens": ["T002"],
            "courseId": "course-eng-001",
            "courseToken": "ENG",
            "courseName": "English",
            "status": "confirmed",
            "color": "#FF5722",
            "eventType": "exam",
            "eventRoomStatus": "reserved",
            "timetableText": "English Language Exam",
            "infoFacilityManagement": None,
            "importset": "2024-2025",
            "lessons": ["3", "4", "5"],
            "publishToInfoSystem": True,
            "studentNames": ["Test User"],
            "studentIds": ["test-user-001"],
            "client": "schulnetz",
            "clientname": "SchulNetz",
            "weight": "2.0"
        }
    ]

def get_mock_absence_notices() -> List[Dict[str, Any]]:
    """Generate mock absence notices matching AbsenceNoticeDto"""
    return [
        {
            "id": "notice-001",
            "studentId": "test-user-001",
            "studentReason": "Family emergency",
            "studentReasonTimestamp": (datetime.now() + timedelta(days=3)).isoformat() + "Z",
            "studentIs18": False,
            "date": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"),
            "hourFrom": "08:00",
            "hourTo": "16:00",
            "time": "08:00-16:00",
            "status": "pending",
            "statusLong": "Pending Approval",
            "comment": "Request for full day absence",
            "isExamLesson": False,
            "profile": "Regular",
            "course": "All Classes",
            "courseId": None,
            "absenceId": "abs-notice-001",
            "absenceSemester": 1,
            "trainerAcknowledgement": None,
            "trainerComment": None,
            "trainerCommentTimestamp": None
        },
        {
            "id": "notice-002",
            "studentId": "test-user-001",
            "studentReason": "Doctor appointment",
            "studentReasonTimestamp": (datetime.now() + timedelta(days=8)).isoformat() + "Z",
            "studentIs18": False,
            "date": (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"),
            "hourFrom": "10:00",
            "hourTo": "12:00",
            "time": "10:00-12:00",
            "status": "approved",
            "statusLong": "Approved by Teacher",
            "comment": "Medical appointment with certificate",
            "isExamLesson": False,
            "profile": "Regular",
            "course": "Mathematics, English",
            "courseId": "course-math-001,course-eng-001",
            "absenceId": "abs-notice-002",
            "absenceSemester": 1,
            "trainerAcknowledgement": "approved",
            "trainerComment": "Approved - medical certificate provided",
            "trainerCommentTimestamp": (datetime.now() + timedelta(days=9)).isoformat() + "Z"
        }
    ]

def get_mock_absence_notice_status() -> List[Dict[str, Any]]:
    """Generate mock absence notice status options matching AbsenceNoticeStatusDto"""
    return [
        {
            "id": "status-001",
            "code": "pending",
            "name": "Pending",
            "sort": "1",
            "comment": "Waiting for approval",
            "additionalInfo": None,
            "iso2": None,
            "iso3": None
        },
        {
            "id": "status-002",
            "code": "approved",
            "name": "Approved",
            "sort": "2",
            "comment": "Approved by teacher",
            "additionalInfo": None,
            "iso2": None,
            "iso3": None
        },
        {
            "id": "status-003",
            "code": "rejected",
            "name": "Rejected",
            "sort": "3",
            "comment": "Rejected by teacher",
            "additionalInfo": None,
            "iso2": None,
            "iso3": None
        },
        {
            "id": "status-004",
            "code": "cancelled",
            "name": "Cancelled",
            "sort": "4",
            "comment": "Cancelled by student",
            "additionalInfo": None,
            "iso2": None,
            "iso3": None
        }
    ]

def get_mock_notifications() -> List[Dict[str, Any]]:
    """Generate mock push notifications (NotificationDto is empty, so flexible structure)"""
    return []  # NotificationDto is an empty class, returns empty list

def get_mock_topics() -> List[Dict[str, Any]]:
    """Generate mock notification topics (TopicDto is empty, so flexible structure)"""
    return []  # TopicDto is an empty class, returns empty list

def get_mock_lateness() -> List[Dict[str, Any]]:
    """Generate mock lateness records matching LatenessDto"""
    return [
        {
            "id": "late-001",
            "dateExcused": None,
            "date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
            "startTime": "08:15",
            "endTime": "08:45",
            "duration": "00:30",
            "reason": "Traffic delay",
            "excused": False,
            "extendedDeadline": 0,
            "courseId": "course-math-001",
            "courseToken": "MATH",
            "comment": "Student arrived 15 minutes late"
        },
        {
            "id": "late-002",
            "dateExcused": (datetime.now() - timedelta(days=9)).strftime("%Y-%m-%d"),
            "date": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
            "startTime": "08:05",
            "endTime": "08:45",
            "duration": "00:05",
            "reason": "Missed bus - public transport delay",
            "excused": True,
            "extendedDeadline": 0,
            "courseId": "course-eng-001",
            "courseToken": "ENG",
            "comment": "Excused - public transport issue confirmed"
        }
    ]

def get_mock_cockpit_report(report_id: int = 1) -> str:
    """Generate mock student ID card HTML"""
    return f"""
    <html>
    <head>
        <title>Student ID Card</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .card {{ border: 2px solid #333; padding: 20px; border-radius: 8px; max-width: 400px; }}
            .header {{ text-align: center; margin-bottom: 20px; }}
            .field {{ margin: 10px 0; }}
            .label {{ font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <h2>Student ID Card</h2>
                <p>Report ID: {report_id}</p>
            </div>
            <div class="field">
                <span class="label">Name:</span> Test User
            </div>
            <div class="field">
                <span class="label">Student ID:</span> 12345678
            </div>
            <div class="field">
                <span class="label">School:</span> Test School
            </div>
            <div class="field">
                <span class="label">Class:</span> 4a
            </div>
            <div class="field">
                <span class="label">Valid from:</span> 2024-01-01
            </div>
            <div class="field">
                <span class="label">Valid until:</span> 2024-12-31
            </div>
            <div class="field">
                <span class="label">Issue Date:</span> {datetime.now().strftime('%Y-%m-%d')}
            </div>
        </div>
    </body>
    </html>
    """

def is_test_token(token: str) -> bool:
    """Check if the provided token is a test token"""
    return token.strip() == TEST_TOKEN

def get_mock_data(data_type: str, **kwargs) -> Optional[Any]:
    """
    Get mock data based on type - returns data matching proper DTOs

    Args:
        data_type: Type of data to return (user_info, events, grades, absences, etc)
        **kwargs: Additional parameters for the data

    Returns:
        Mock data matching the appropriate DTO structure, or None if type is not recognized
        
    Note: Most endpoints return List[DTO], but user_info returns a single Dict
    """
    data_generators = {
        "user_info": get_mock_user_info,  # Returns Dict (single UserInfoDto)
        "events": lambda: get_mock_events(kwargs.get("min_date"), kwargs.get("max_date")),  # Returns List[AgendaDto]
        "grades": get_mock_grades,  # Returns List[GradeDto]
        "absences": get_mock_absences,  # Returns List[AbsenceDto]
        "timetable": get_mock_timetable,  # Returns List[AgendaDto]
        "documents": get_mock_documents,  # Returns List[Dict] (no specific DTO)
        "settings": get_mock_settings,  # Returns List[SettingDto]
        "exams": get_mock_exams,  # Returns List[ExamDto]
        "absencenotices": get_mock_absence_notices,  # Returns List[AbsenceNoticeDto]
        "absencenoticestatus": get_mock_absence_notice_status,  # Returns List[AbsenceNoticeStatusDto]
        "notifications": get_mock_notifications,  # Returns List (empty - NotificationDto is empty)
        "topics": get_mock_topics,  # Returns List (empty - TopicDto is empty)
        "lateness": get_mock_lateness,  # Returns List[LatenessDto]
        "cockpitreport": lambda: get_mock_cockpit_report(kwargs.get("report_id", 1)),  # Returns HTML string
    }

    generator = data_generators.get(data_type)
    if generator:
        return generator()
    return None
