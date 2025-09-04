from peewee import CharField, IntegerField, ForeignKeyField
from .base import BaseModel
from .user import User

class WebUrl(BaseModel):
    user = ForeignKeyField(User, backref='web_urls', unique=True)
    start = CharField()
    grades = CharField()
    absent_notices = CharField()
    lesson = CharField()
    agenda = CharField()
    documents = CharField()
    student_id_card = CharField()

class MobileSession(BaseModel):
    user = ForeignKeyField(User, backref='mobile_sessions', unique=True)
    access_token = CharField()
    refresh_token = CharField()
    expires_in = IntegerField()

class WebSession(BaseModel):
    user = ForeignKeyField(User, backref='web_sessions', unique=True)
    php_session_id = CharField()