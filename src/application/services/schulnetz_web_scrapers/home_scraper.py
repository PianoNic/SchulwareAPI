import httpx
from bs4 import BeautifulSoup
from typing import List

async def scrape_home(url: str) -> List[dict]:
 return