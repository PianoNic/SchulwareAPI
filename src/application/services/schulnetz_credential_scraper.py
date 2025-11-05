import httpx

async def get_credentials(schulnetz_url: str):       
    async with httpx.AsyncClient() as client:
        
        response = await client.get(schulnetz_url)
        response.raise_for_status()
        
        return {
            "status_code": response.status_code,
            "content": response.text,
            "headers": dict(response.headers),
            "url": str(response.url)
        }
      