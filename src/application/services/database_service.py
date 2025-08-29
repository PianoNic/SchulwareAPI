import json
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse, parse_qs

from peewee import DoesNotExist, IntegrityError
from fastapi import HTTPException

from ..models.auth_models import db, AuthSession, NavigationRoute, AuthLog, create_tables
import logging

# Set up logger
logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for managing authentication database operations."""
    
    def __init__(self):
        """Initialize the database service and ensure tables exist."""
        create_tables()
    
    def __enter__(self):
        """Context manager entry."""
        db.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if not db.is_closed():
            db.close()
    
    # --- Session Management ---
    
    def create_session(
        self,
        email: str,
        auth_type: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        auth_code: Optional[str] = None,
        session_cookies: Optional[Dict[str, str]] = None,
        navigation_urls: Optional[Dict[str, str]] = None,
        noten_url: Optional[str] = None,
        redirect_domain: Optional[str] = None,
        expires_in_hours: int = 24
    ) -> str:
        """
        Create a new authentication session.
        
        Args:
            email: User email
            auth_type: Type of authentication ('mobile', 'web', 'unified')
            access_token: OAuth2 access token (for mobile/unified)
            refresh_token: OAuth2 refresh token (for mobile/unified)
            auth_code: Authorization code
            session_cookies: Session cookies dictionary (for web/unified)
            navigation_urls: Navigation URLs dictionary
            noten_url: Direct URL to grades page
            redirect_domain: Domain used for redirect
            expires_in_hours: Session expiration time in hours
            
        Returns:
            session_id: Unique session identifier
        """
        with db.atomic():
            try:
                # Generate unique session ID
                session_id = str(uuid.uuid4())
                
                # Calculate expiration time
                expires_at = datetime.now() + timedelta(hours=expires_in_hours)
                
                # Create session
                session = AuthSession.create(
                    session_id=session_id,
                    email=email,
                    auth_type=auth_type,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    auth_code=auth_code,
                    noten_url=noten_url,
                    redirect_domain=redirect_domain,
                    expires_at=expires_at
                )
                
                # Set cookies and navigation data
                if session_cookies:
                    session.cookies_dict = session_cookies
                
                if navigation_urls:
                    session.navigation_dict = navigation_urls
                
                session.save()
                
                # Create navigation routes from navigation_urls
                if navigation_urls:
                    self._create_navigation_routes(session, navigation_urls)
                
                # Log successful session creation
                self.log_event(
                    session_id=session_id,
                    event_type="login",
                    auth_type=auth_type,
                    message=f"Session created for {email}",
                    success=True
                )
                
                logger.info(f"Created {auth_type} session {session_id} for {email}")
                return session_id
                
            except IntegrityError as e:
                logger.error(f"Database integrity error creating session: {e}")
                raise HTTPException(status_code=500, detail="Failed to create session")
            except Exception as e:
                logger.error(f"Error creating session: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
    
    def get_session(self, session_id: str) -> Optional[AuthSession]:
        """Get session by ID."""
        try:
            with db.atomic():
                return AuthSession.get(
                    (AuthSession.session_id == session_id) & 
                    (AuthSession.is_active == True)
                )
        except DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {e}")
            return None
    
    def get_active_session_by_email_and_type(self, email: str, auth_type: str) -> Optional[AuthSession]:
        """Get the most recent active session for a user and auth type."""
        try:
            with db.atomic():
                return (AuthSession
                       .select()
                       .where(
                           (AuthSession.email == email) & 
                           (AuthSession.auth_type == auth_type) & 
                           (AuthSession.is_active == True)
                       )
                       .order_by(AuthSession.created_at.desc())
                       .first())
        except Exception as e:
            logger.error(f"Error retrieving session for {email}, {auth_type}: {e}")
            return None
    
    def update_session_tokens(
        self,
        session_id: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        expires_in_hours: Optional[int] = None
    ) -> bool:
        """Update session tokens."""
        try:
            with db.atomic():
                session = self.get_session(session_id)
                if not session:
                    return False
                
                if access_token is not None:
                    session.access_token = access_token
                
                if refresh_token is not None:
                    session.refresh_token = refresh_token
                
                if expires_in_hours is not None:
                    session.expires_at = datetime.now() + timedelta(hours=expires_in_hours)
                
                session.save()
                
                self.log_event(
                    session_id=session_id,
                    event_type="token_refresh",
                    auth_type=session.auth_type,
                    message="Session tokens updated",
                    success=True
                )
                
                return True
        except Exception as e:
            logger.error(f"Error updating session tokens: {e}")
            return False
    
    def deactivate_session(self, session_id: str) -> bool:
        """Deactivate a session."""
        try:
            with db.atomic():
                session = self.get_session(session_id)
                if not session:
                    return False
                
                session.is_active = False
                session.save()
                
                self.log_event(
                    session_id=session_id,
                    event_type="logout",
                    auth_type=session.auth_type,
                    message="Session deactivated",
                    success=True
                )
                
                return True
        except Exception as e:
            logger.error(f"Error deactivating session: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions and return count of removed sessions."""
        try:
            with db.atomic():
                expired_count = (AuthSession
                               .delete()
                               .where(
                                   (AuthSession.expires_at < datetime.now()) |
                                   (AuthSession.is_active == False)
                               )
                               .execute())
                
                if expired_count > 0:
                    logger.info(f"Cleaned up {expired_count} expired sessions")
                
                return expired_count
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return 0
    
    # --- Navigation Routes Management ---
    
    def _create_navigation_routes(self, session: AuthSession, navigation_urls: Dict[str, str]) -> None:
        """Create navigation routes from navigation URLs dictionary."""
        for route_name, route_url in navigation_urls.items():
            try:
                # Parse URL to extract parameters
                parsed_url = urlparse(route_url)
                query_params = parse_qs(parsed_url.query)
                
                # Extract page_id if present
                page_id = query_params.get('pageid', [None])[0]
                
                # Generate keywords for searching
                keywords = self._generate_keywords(route_name, route_url)
                
                # Determine category based on route name
                category = self._categorize_route(route_name)
                
                # Create or update route
                route, created = NavigationRoute.get_or_create(
                    session=session,
                    route_name=route_name,
                    defaults={
                        'route_url': route_url,
                        'page_id': page_id,
                        'category': category,
                        'keywords': keywords,
                        'parameters_dict': dict(query_params) if query_params else {}
                    }
                )
                
                if not created:
                    # Update existing route
                    route.route_url = route_url
                    route.page_id = page_id
                    route.category = category
                    route.keywords = keywords
                    route.parameters_dict = dict(query_params) if query_params else {}
                    route.save()
                
                logger.debug(f"{'Created' if created else 'Updated'} route: {route_name}")
                
            except Exception as e:
                logger.warning(f"Error creating route {route_name}: {e}")
                continue
    
    def _generate_keywords(self, route_name: str, route_url: str) -> str:
        """Generate search keywords from route name and URL."""
        keywords = set()
        
        # Add route name words
        keywords.update(route_name.lower().split())
        
        # Add URL components
        parsed_url = urlparse(route_url)
        if parsed_url.path:
            keywords.update(parsed_url.path.lower().split('/'))
        
        # Add query parameter values
        query_params = parse_qs(parsed_url.query)
        for param_values in query_params.values():
            for value in param_values:
                if value and len(value) > 2:  # Skip very short values
                    keywords.update(value.lower().split())
        
        return ' '.join(keywords)
    
    def _categorize_route(self, route_name: str) -> str:
        """Categorize route based on its name."""
        route_lower = route_name.lower()
        
        if any(word in route_lower for word in ['noten', 'grade', 'bewertung']):
            return 'grades'
        elif any(word in route_lower for word in ['agenda', 'kalender', 'termine']):
            return 'calendar'
        elif any(word in route_lower for word in ['unterricht', 'stundenplan', 'schedule']):
            return 'schedule'
        elif any(word in route_lower for word in ['listen', 'list', 'übersicht']):
            return 'lists'
        elif any(word in route_lower for word in ['ausweis', 'profil', 'profile']):
            return 'profile'
        else:
            return 'general'
    
    def get_navigation_routes(
        self,
        session_id: str,
        category: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get navigation routes for a session with optional filtering."""
        try:
            session = self.get_session(session_id)
            if not session:
                return []
            
            query = NavigationRoute.select().where(NavigationRoute.session == session)
            
            if category:
                query = query.where(NavigationRoute.category == category)
            
            if search_query:
                search_conditions = (
                    (NavigationRoute.route_name.contains(search_query)) |
                    (NavigationRoute.keywords.contains(search_query.lower()))
                )
                query = query.where(search_conditions)
            
            routes = []
            for route in query.order_by(NavigationRoute.route_name):
                routes.append({
                    'route_name': route.route_name,
                    'route_url': route.route_url,
                    'page_id': route.page_id,
                    'category': route.category,
                    'parameters': route.parameters_dict,
                    'access_count': route.access_count,
                    'last_accessed': route.last_accessed.isoformat() if route.last_accessed else None,
                    'is_accessible': route.is_accessible
                })
            
            return routes
            
        except Exception as e:
            logger.error(f"Error retrieving navigation routes: {e}")
            return []
    
    def record_route_access(self, session_id: str, route_name: str) -> bool:
        """Record that a route was accessed."""
        try:
            session = self.get_session(session_id)
            if not session:
                return False
            
            route = NavigationRoute.get(
                (NavigationRoute.session == session) &
                (NavigationRoute.route_name == route_name)
            )
            
            route.record_access()
            return True
            
        except DoesNotExist:
            logger.warning(f"Route {route_name} not found for session {session_id}")
            return False
        except Exception as e:
            logger.error(f"Error recording route access: {e}")
            return False
    
    def save_navigation_route(self, session_id: str, route_name: str, route_url: str, route_type: str = "navigation_menu") -> None:
        """Save a single navigation route for a session."""
        try:
            session = self.get_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found for saving navigation route {route_name}")
                return
            navigation_urls = {route_name: route_url}
            self._create_navigation_routes(session, navigation_urls)
        except Exception as e:
            logger.warning(f"Error saving navigation route {route_name} for session {session_id}: {e}")
    
    # --- Logging ---
    
    def log_event(
        self,
        event_type: str,
        auth_type: str,
        message: str,
        session_id: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Log an authentication event."""
        try:
            with db.atomic():
                session = None
                if session_id:
                    session = self.get_session(session_id)
                
                log_entry = AuthLog.create(
                    session=session,
                    event_type=event_type,
                    auth_type=auth_type,
                    message=message,
                    success=success,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if details:
                    log_entry.details_dict = details
                    log_entry.save()
                
        except Exception as e:
            logger.error(f"Error logging event: {e}")
    
    def get_session_logs(
        self,
        session_id: str,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get logs for a specific session."""
        try:
            session = self.get_session(session_id)
            if not session:
                return []
            
            query = (AuthLog
                    .select()
                    .where(AuthLog.session == session)
                    .order_by(AuthLog.created_at.desc())
                    .limit(limit))
            
            if event_type:
                query = query.where(AuthLog.event_type == event_type)
            
            logs = []
            for log in query:
                logs.append({
                    'event_type': log.event_type,
                    'auth_type': log.auth_type,
                    'message': log.message,
                    'success': log.success,
                    'details': log.details_dict,
                    'ip_address': log.ip_address,
                    'user_agent': log.user_agent,
                    'created_at': log.created_at.isoformat()
                })
            
            return logs
            
        except Exception as e:
            logger.error(f"Error retrieving session logs: {e}")
            return []
    
    # --- Utility Methods ---
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive session information."""
        try:
            session = self.get_session(session_id)
            if not session:
                return None
            
            return {
                'session_id': session.session_id,
                'email': session.email,
                'auth_type': session.auth_type,
                'has_access_token': bool(session.access_token),
                'has_refresh_token': bool(session.refresh_token),
                'has_cookies': bool(session.session_cookies),
                'navigation_urls': session.navigation_dict,
                'noten_url': session.noten_url,
                'redirect_domain': session.redirect_domain,
                'authenticated_at': session.authenticated_at.isoformat(),
                'expires_at': session.expires_at.isoformat() if session.expires_at else None,
                'is_active': session.is_active,
                'route_count': session.routes.count(),
                'last_activity': session.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error retrieving session info: {e}")
            return None
    
    def search_routes_across_sessions(
        self,
        email: str,
        search_query: str,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search routes across all sessions for a user."""
        try:
            # Get all active sessions for the user
            sessions = (AuthSession
                       .select()
                       .where(
                           (AuthSession.email == email) &
                           (AuthSession.is_active == True)
                       ))
            
            routes = []
            for session in sessions:
                session_routes = self.get_navigation_routes(
                    session.session_id,
                    category=category,
                    search_query=search_query
                )
                
                # Add session context to each route
                for route in session_routes:
                    route['session_id'] = session.session_id
                    route['auth_type'] = session.auth_type
                    routes.append(route)
            
            # Sort by access count and relevance
            routes.sort(key=lambda x: (-x['access_count'], x['route_name']))
            return routes
            
        except Exception as e:
            logger.error(f"Error searching routes for user {email}: {e}")
            return []

# Create a global instance
db_service = DatabaseService()
