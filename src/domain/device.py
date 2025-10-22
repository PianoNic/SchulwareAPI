from peewee import CharField, BooleanField, ForeignKeyField
from .base import BaseModel
from .user import User

class Device(BaseModel):
    """Stores device registration for push notifications"""
    user = ForeignKeyField(User, backref='devices')
    platform = CharField()  # 'ios' or 'android'
    has_gms = BooleanField(default=True)  # Google Mobile Services available
    push_token = CharField(null=True)  # APNs token or FCM token
    ntfy_endpoint = CharField(null=True)  # For UnifiedPush/ntfy
    device_name = CharField(null=True)  # Optional: "iPhone 14", "Pixel 7"
    is_active = BooleanField(default=True)  # For soft-delete

    class Meta:
        indexes = (
            (('user', 'platform', 'push_token'), True),  # Unique per user+platform+token
        )
