import httpx
from bs4 import BeautifulSoup
from typing import List

async def scrape_noten(url: str) -> List[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
    if resp.status_code != 200:
        raise Exception(f"Failed to fetch {url}: {resp.status_code}")
    soup = BeautifulSoup(resp.text, "html.parser")
    # Example: extract grades from table
    items = []
    for row in soup.select("table.noten-table tr"):
        items.append({"noten": row.get_text(strip=True)})
    return items
