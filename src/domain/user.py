from peewee import CharField
from .base import BaseModel

class User(BaseModel):
    email = CharField(unique=True)