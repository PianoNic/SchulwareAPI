import httpx
from bs4 import BeautifulSoup
from typing import List

async def scrape_ausweis(url: str) -> List[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
    if resp.status_code != 200:
        raise Exception(f"Failed to fetch {url}: {resp.status_code}")
    soup = BeautifulSoup(resp.text, "html.parser")
    # Example: extract ausweis info
    items = []
    for div in soup.select("div.ausweis-info"):
        items.append({"info": div.get_text(strip=True)})
    return items
