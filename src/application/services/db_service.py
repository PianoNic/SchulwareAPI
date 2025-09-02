from src.application.dtos.auth_dto import MobileSessionDto, WebSessionDto
from src.application.dtos.user_dto import UserDto
from src.infrastructure.database import database
from src.domain.user import User
from src.domain.auth import MobileSession, WebSession
from fastapi.logger import logger

ALL_MODELS = [User, MobileSession, WebSession]

def setup_db():
    database.bind(ALL_MODELS, bind_refs=False, bind_backrefs=False)
    database.connect()

    logger.info("Creating tables...")
    database.create_tables(ALL_MODELS)
    logger.info("Tables created.")

    database.close()
    logger.info("Database connection closed.")
    
def create_or_update_user(user_email: str, mobile_session_dto: MobileSessionDto, web_session_dto: WebSessionDto):
    database.connect()
    
    user, user_created = User.get_or_create(email=user_email)
    
    mobile_session, mobile_created = MobileSession.get_or_create(
        user=user,
        defaults={
            'access_token': mobile_session_dto.access_token,
            'refresh_token': mobile_session_dto.refresh_token,
            'expires_in': mobile_session_dto.expires_in
        }
    )
    
    if not mobile_created:
        mobile_session.access_token = mobile_session_dto.access_token
        mobile_session.refresh_token = mobile_session_dto.refresh_token
        mobile_session.expires_in = mobile_session_dto.expires_in
        mobile_session.save()
        logger.info(f"Updated mobile session for user: {user_email}")
    else:
        logger.info(f"Created new mobile session for user: {user_email}")
    
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
    
    database.close()