import httpx
from typing import Optional, Dict, Any
from src.application.services.env_service import get_env_variable
from src.application.services.token_service import token_service, ApplicationType
from fastapi.logger import logger

class SchulnetzMobileService:
    def __init__(self):
        self.base_url = get_env_variable("SCHULNETZ_API_BASE_URL")
        self.client_id = get_env_variable("SCHULNETZ_CLIENT_ID")
    
    async def get_user_info(self, user_id: str) -> Optional[Dict]:
        """Get user information from mobile API"""
        token = token_service.get_valid_access_token(user_id, ApplicationType.MOBILE_API)
        if not token:
            return None
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
            "Referer": "https://schulnetz.web.app/"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/rest/v1/me", headers=headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to get user info: {e}")
                return None
    
    async def get_events(self, user_id: str, min_date: Optional[str] = None, 
                        max_date: Optional[str] = None) -> Optional[Dict]:
        """Get user events from mobile API"""
        token = token_service.get_valid_access_token(user_id, ApplicationType.MOBILE_API)
        if not token:
            return None
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
            "Referer": "https://schulnetz.web.app/"
        }
        
        params = {}
        if min_date:
            params["min_date"] = min_date
        if max_date:
            params["max_date"] = max_date
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/rest/v1/me/events", 
                                          headers=headers, params=params)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to get events: {e}")
                return None
    
    async def get_grades(self, user_id: str) -> Optional[Dict]:
        """Get user grades from mobile API"""
        token = token_service.get_valid_access_token(user_id, ApplicationType.MOBILE_API)
        if not token:
            return None
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
            "Referer": "https://schulnetz.web.app/"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/rest/v1/me/grades", headers=headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to get grades: {e}")
                return None
    
    async def proxy_request(self, user_id: str, endpoint: str, method: str = "GET", 
                           params: Dict = None, data: Any = None) -> Optional[httpx.Response]:
        """Generic proxy method for mobile API requests"""
        token = token_service.get_valid_access_token(user_id, ApplicationType.MOBILE_API)
        if not token:
            return None
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
            "Referer": "https://schulnetz.web.app/"
        }
        
        # Ensure endpoint starts with /rest/v1/
        if not endpoint.startswith("/rest/v1/"):
            endpoint = f"/rest/v1/{endpoint.lstrip('/')}"
        
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method, url, headers=headers, params=params, json=data
                )
                return response
            except Exception as e:
                logger.error(f"Failed to proxy mobile request: {e}")
                return None

# Global instance
mobile_service = SchulnetzMobileService()