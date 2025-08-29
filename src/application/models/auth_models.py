from datetime import datetime
from peewee import *
import json
import os

# Create database in the project root or use environment variable
db_path = os.getenv("DATABASE_PATH", "schulware_auth.db")
db = SqliteDatabase(db_path)

class BaseModel(Model):
    """Base model class that binds to our database."""
    class Meta:
        database = db

class AuthSession(BaseModel):
    """Model for storing authentication sessions across different auth types."""
    
    # Session identification
    session_id = CharField(unique=True, max_length=255)
    email = CharField(max_length=255, index=True)
    auth_type = CharField(max_length=20, index=True)  # 'mobile', 'web', 'unified'
    
    # OAuth2 tokens (for mobile and unified)
    access_token = TextField(null=True)
    refresh_token = TextField(null=True)
    auth_code = CharField(max_length=500, null=True)
    
    # Session cookies (for web and unified) - stored as JSON
    session_cookies = TextField(null=True)
    
    # Navigation data - stored as JSON
    navigation_urls = TextField(null=True)
    noten_url = CharField(max_length=500, null=True)
    
    # Metadata
    redirect_domain = CharField(max_length=100, null=True)
    authenticated_at = DateTimeField(default=datetime.now)
    expires_at = DateTimeField(null=True)
    is_active = BooleanField(default=True)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)
    
    def save(self, *args, **kwargs):
        """Override save to update the updated_at timestamp."""
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)
    
    @property
    def cookies_dict(self):
        """Get session cookies as a dictionary."""
        if self.session_cookies:
            try:
                return json.loads(self.session_cookies)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @cookies_dict.setter
    def cookies_dict(self, value):
        """Set session cookies from a dictionary."""
        if value:
            self.session_cookies = json.dumps(value)
        else:
            self.session_cookies = None
    
    @property
    def navigation_dict(self):
        """Get navigation URLs as a dictionary."""
        if self.navigation_urls:
            try:
                return json.loads(self.navigation_urls)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @navigation_dict.setter
    def navigation_dict(self, value):
        """Set navigation URLs from a dictionary."""
        if value:
            self.navigation_urls = json.dumps(value)
        else:
            self.navigation_urls = None

    class Meta:
        # Index combinations for better query performance
        indexes = (
            (('email', 'auth_type'), False),
            (('email', 'is_active'), False),
            (('auth_type', 'is_active'), False),
        )

class NavigationRoute(BaseModel):
    """Model for storing extracted navigation routes with search optimization."""
    
    # Route identification
    route_name = CharField(max_length=255, index=True)
    route_url = CharField(max_length=1000)
    page_id = CharField(max_length=100, null=True, index=True)
    
    # Associated session
    session = ForeignKeyField(AuthSession, backref='routes', on_delete='CASCADE')
    
    # Search and categorization
    category = CharField(max_length=100, null=True, index=True)
    description = TextField(null=True)
    keywords = CharField(max_length=500, null=True, index=True)  # Space-separated keywords for search
    
    # Route parameters for dynamic URLs
    parameters = TextField(null=True)  # JSON of common parameters
    
    # Status tracking
    is_accessible = BooleanField(default=True)
    last_accessed = DateTimeField(null=True)
    access_count = IntegerField(default=0)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)
    
    def save(self, *args, **kwargs):
        """Override save to update the updated_at timestamp."""
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)
    
    @property
    def parameters_dict(self):
        """Get route parameters as a dictionary."""
        if self.parameters:
            try:
                return json.loads(self.parameters)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @parameters_dict.setter
    def parameters_dict(self, value):
        """Set route parameters from a dictionary."""
        if value:
            self.parameters = json.dumps(value)
        else:
            self.parameters = None
    
    def record_access(self):
        """Record that this route was accessed."""
        self.last_accessed = datetime.now()
        self.access_count += 1
        self.save()
    
    @classmethod
    def search_routes(cls, query, session_id=None, category=None):
        """Search routes by keywords, name, or description."""
        conditions = []
        
        if query:
            query_conditions = (
                (cls.route_name.contains(query)) |
                (cls.description.contains(query)) |
                (cls.keywords.contains(query))
            )
            conditions.append(query_conditions)
        
        if session_id:
            conditions.append(cls.session == session_id)
            
        if category:
            conditions.append(cls.category == category)
        
        if conditions:
            return cls.select().where(*conditions)
        else:
            return cls.select()

    class Meta:
        # Ensure unique routes per session
        indexes = (
            (('session', 'route_name'), True),  # Unique constraint
            (('category', 'is_accessible'), False),
            (('keywords',), False),  # For text search
        )

class AuthLog(BaseModel):
    """Model for logging authentication events and errors."""
    
    # Log identification
    session = ForeignKeyField(AuthSession, backref='logs', on_delete='CASCADE', null=True)
    event_type = CharField(max_length=50, index=True)  # 'login', 'logout', 'token_refresh', 'error'
    auth_type = CharField(max_length=20, index=True)
    
    # Event details
    message = TextField()
    details = TextField(null=True)  # JSON for additional context
    success = BooleanField(default=True)
    
    # Request context
    ip_address = CharField(max_length=45, null=True)
    user_agent = CharField(max_length=500, null=True)
    
    # Timestamp
    created_at = DateTimeField(default=datetime.now, index=True)
    
    @property
    def details_dict(self):
        """Get event details as a dictionary."""
        if self.details:
            try:
                return json.loads(self.details)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @details_dict.setter
    def details_dict(self, value):
        """Set event details from a dictionary."""
        if value:
            self.details = json.dumps(value)
        else:
            self.details = None

# List of all models for easy database management
MODELS = [AuthSession, NavigationRoute, AuthLog]

def create_tables():
    """Create all database tables."""
    db.connect()
    db.create_tables(MODELS, safe=True)
    db.close()

def drop_tables():
    """Drop all database tables (use with caution)."""
    db.connect()
    db.drop_tables(MODELS, safe=True)
    db.close()
