import httpx
from src.application.services.env_service import get_env_variable
from urllib.parse import urlencode

async def get_schulnetz_web_html_authenticated(pageid: str, id: str, transid: str, php_sessid: str) -> str:
    base_url = get_env_variable("SCHULNETZ_API_BASE_URL")
    query_params = {
        "pageid": pageid,
        "id": id,
        "transid": transid
    }
    url = f"{base_url}/index.php?{urlencode(query_params)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
        "Cookie": f"PHPSESSID={php_sessid}; layout-size=sm"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.text
        except Exception:
            return None