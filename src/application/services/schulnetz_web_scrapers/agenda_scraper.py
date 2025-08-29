import httpx
from bs4 import BeautifulSoup
from typing import List

async def scrape_agenda(url: str) -> List[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
    if resp.status_code != 200:
        raise Exception(f"Failed to fetch {url}: {resp.status_code}")
    soup = BeautifulSoup(resp.text, "html.parser")
    # Example: extract agenda items
    items = []
    for item in soup.select(".agenda-item"):
        items.append({"agenda": item.get_text(strip=True)})
    return items
