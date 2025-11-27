from src.application.dtos.web.web_urls_dto import WebUrlsDto
from src.application.dtos.auth_dto import MobileSessionDto, WebSessionDto
from src.infrastructure.database import database
from src.domain.user import User
from src.domain.auth import WebSession, WebUrl
from src.infrastructure.logging_config import get_logger

# Logger for this module
logger = get_logger("database")

ALL_MODELS = [User, WebSession, WebUrl]

def setup_db():
    database.bind(ALL_MODELS, bind_refs=False, bind_backrefs=False)
    database.connect()

    logger.info("Creating tables...")
    database.create_tables(ALL_MODELS)
    logger.info("Tables created.")

    database.close()
    logger.info("Database connection closed.")
    
def create_or_update_user(user_email: str, web_session_dto: WebSessionDto = None, web_url_dto: WebUrlsDto=None):
    if not user_email:
        raise ValueError("user_email cannot be null or empty.")

    database.connect()

    user, user_created = User.get_or_create(email=user_email)

    if web_session_dto is not None:
        web_session, web_created = WebSession.get_or_create(
            user=user,
            defaults={
                'php_session_id': web_session_dto.php_session_id
            }
        )

        if not web_created:
            web_session.php_session_id = web_session_dto.php_session_id
            web_session.save()
            logger.info(f"Updated web session for user: {user_email}")
        else:
            logger.info(f"Created new web session for user: {user_email}")

    if web_url_dto is not None:
        web_url, web_url_created = WebUrl.get_or_create(
            user=user,
            defaults={
                'start': web_url_dto.start,
                'grades': web_url_dto.grades,
                'absent_notices': web_url_dto.absent_notices,
                'lesson': web_url_dto.lesson,
                'agenda': web_url_dto.agenda,
                'documents': web_url_dto.documents,
                'student_id_card': web_url_dto.student_id_card
            }
        )

        if not web_url_created:
            web_url.start = web_url_dto.start
            web_url.grades = web_url_dto.grades
            web_url.absent_notices = web_url_dto.absent_notices
            web_url.lesson = web_url_dto.lesson
            web_url.agenda = web_url_dto.agenda
            web_url.documents = web_url_dto.documents
            web_url.student_id_card = web_url_dto.student_id_card
            web_url.save()
            logger.info(f"Updated web urls for user: {user_email}")
        else:
            logger.info(f"Created new web urls for user: {user_email}")

    database.close()