import httpx
from bs4 import BeautifulSoup
from typing import List

async def scrape_unterricht(url: str) -> List[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
    if resp.status_code != 200:
        raise Exception(f"Failed to fetch {url}: {resp.status_code}")
    soup = BeautifulSoup(resp.text, "html.parser")
    # Example: extract all table rows in Unterricht section
    items = []
    for row in soup.select("table.unterricht-table tr"):
        items.append({"row": row.get_text(strip=True)})
    return items
