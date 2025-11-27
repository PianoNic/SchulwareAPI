from typing import Optional, Tuple
import httpx
from src.infrastructure.logging_config import get_logger
from src.application.services.env_service import get_env_variable

# Logger for this module
logger = get_logger("token_manager")

class ApplicationType:
    MOBILE_API = "mobile_api"
    WEB_INTERFACE = "web_interface"

class TokenService:
    def __init__(self):
        self.client_id = get_env_variable("SCHULNETZ_CLIENT_ID")

    async def refresh_mobile_token(self, refresh_token: str) -> Tuple[Optional[str], Optional[str]]:
        """Refresh mobile API token"""
        token_url = "https://schulnetz.bbbaden.ch/token.php"
        
        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://schulnetz.web.app/",
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(token_url, data=token_data, headers=headers)
                response.raise_for_status()
                
                token_json = response.json()
                new_access_token = token_json.get("access_token")
                new_refresh_token = token_json.get("refresh_token", refresh_token)
                expires_in = token_json.get("expires_in", 3600)
                
                if new_access_token:
                    return new_access_token, new_refresh_token
                else:
                    logger.error("No access token in mobile refresh response")
                    return None, None
                
            except Exception as e:
                logger.error(f"Failed to refresh mobile token: {e}")
                return None, None

# Global instance
token_service = TokenService()