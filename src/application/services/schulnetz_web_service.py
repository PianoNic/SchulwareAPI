import httpx
from typing import Optional, Dict, Any
from src.infrastructure.logging_config import get_logger
from src.infrastructure.monitoring import monitor_performance, add_breadcrumb, capture_exception
from src.application.services.env_service import get_env_variable
from src.application.services.token_service import token_service, ApplicationType

# Logger for this module
logger = get_logger("web_scraper")

class SchulnetzWebService:
    def __init__(self):
        self.base_url = get_env_variable("SCHULNETZ_WEB_BASE_URL")
        self.client_id = get_env_variable("SCHULNETZ_CLIENT_ID")
    
    def _get_web_session_cookies(self, user_id: str) -> Dict[str, str]:
        """Get web session cookies from stored session data"""
        session_data = token_service.get_session_data(user_id, ApplicationType.WEB_INTERFACE)
        return session_data.get("cookies", {})
    
    def _get_web_headers(self, user_id: str) -> Dict[str, str]:
        """Get standard headers for web requests"""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7,fr;q=0.6,no;q=0.5,es;q=0.4",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Upgrade-Insecure-Requests": "1",
            "sec-ch-ua": '"Opera";v="120", "Not-A.Brand";v="8", "Chromium";v="135"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"'
        }
    
    @monitor_performance("web.scraping.dashboard")
    async def get_dashboard(self, user_id: str) -> Optional[str]:
        """Get main dashboard HTML"""
        add_breadcrumb(
            message="Fetching web dashboard",
            category="web.scraping",
            level="info"
        )
        cookies = self._get_web_session_cookies(user_id)
        headers = self._get_web_headers(user_id)

        if not cookies:
            logger.error("No web session cookies found")
            return None

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/index.php",
                    headers=headers,
                    cookies=cookies
                )
                response.raise_for_status()
                return response.text
            except Exception as e:
                capture_exception(
                    e,
                    context={
                        "operation": "get_dashboard",
                        "user_id": user_id
                    },
                    level="error"
                )
                logger.error(f"Failed to get dashboard: {e}")
                return None
    
    @monitor_performance("web.scraping.page")
    async def get_page(self, user_id: str, page_id: str,
                      additional_params: Dict[str, str] = None) -> Optional[str]:
        """Get specific page by page ID"""
        add_breadcrumb(
            message=f"Fetching web page: {page_id}",
            category="web.scraping",
            level="info",
            data={"page_id": page_id}
        )
        cookies = self._get_web_session_cookies(user_id)
        headers = self._get_web_headers(user_id)

        if not cookies:
            logger.error("No web session cookies found")
            return None

        params = {"pageid": page_id}
        if additional_params:
            params.update(additional_params)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/index.php",
                    headers=headers,
                    cookies=cookies,
                    params=params
                )
                response.raise_for_status()
                return response.text
            except Exception as e:
                capture_exception(
                    e,
                    context={
                        "operation": "get_page",
                        "user_id": user_id,
                        "page_id": page_id
                    },
                    level="error"
                )
                logger.error(f"Failed to get page {page_id}: {e}")
                return None
    
    async def proxy_web_request(self, user_id: str, path: str, method: str = "GET",
                               params: Dict = None, data: Any = None) -> Optional[httpx.Response]:
        """Generic proxy method for web requests"""
        cookies = self._get_web_session_cookies(user_id)
        headers = self._get_web_headers(user_id)
        
        if not cookies:
            logger.error("No web session cookies found")
            return None
        
        # Build full URL
        if path.startswith("/"):
            url = f"{self.base_url}{path}"
        else:
            url = f"{self.base_url}/{path}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method, url, 
                    headers=headers, 
                    cookies=cookies,
                    params=params,
                    data=data
                )
                return response
            except Exception as e:
                logger.error(f"Failed to proxy web request: {e}")
                return None
    
    async def extract_session_info(self, response_text: str, response_cookies: Dict) -> Dict:
        """Extract session information from web response"""
        session_info = {
            "cookies": response_cookies,
            "extracted_at": str(httpx._utils.default_ssl_context)  # Use current time
        }
        
        # You can add more session extraction logic here
        # For example, extracting CSRF tokens, user IDs, etc. from the HTML
        
        return session_info

# Global instance
web_service = SchulnetzWebService()