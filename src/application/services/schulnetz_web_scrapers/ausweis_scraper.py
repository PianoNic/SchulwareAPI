from bs4 import BeautifulSoup

def scrape_ausweis(html: str) -> dict[str, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    info = {}

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if key:
                    info[key] = value

    img = soup.find("img", src=lambda s: s and "qr" in s.lower())
    if img:
        info["qr_code_url"] = img.get("src")

    return info
