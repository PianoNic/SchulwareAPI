import re
import json
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from datetime import datetime, timedelta


def scrape_agenda(html: str) -> Dict[str, Any]:
    """
    Parse the agenda page. The agenda uses a JavaScript scheduler widget,
    so we extract metadata and the scheduler config from the HTML.
    Actual event data needs to be fetched via scheduler_processor.php.
    """
    soup = BeautifulSoup(html, "html.parser")

    result = {
        "events": [],
        "scheduler_config": None,
    }

    for table in soup.find_all("table"):
        header_row = table.find("tr")
        if not header_row:
            continue

        headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]
        if "datum" not in " ".join(headers):
            continue

        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            item = {}
            for i, h in enumerate(headers):
                if i < len(cells):
                    item[h] = re.sub(r'\s+', ' ', cells[i].get_text()).strip()

            if any(v for v in item.values()):
                result["events"].append(item)

    for script in soup.find_all("script"):
        text = script.string or ""
        if "scheduler_processor" in text:
            result["scheduler_config"] = _extract_scheduler_url(text)
            break

    return result


def _extract_scheduler_url(script_text: str) -> Dict[str, str]:
    config = {}

    pageid_match = re.search(r'pageid[=:](\d+)', script_text)
    if pageid_match:
        config["pageid"] = pageid_match.group(1)

    id_match = re.search(r'[&?]id=([a-f0-9]+)', script_text)
    if id_match:
        config["id"] = id_match.group(1)

    transid_match = re.search(r'transid=([a-f0-9]+)', script_text)
    if transid_match:
        config["transid"] = transid_match.group(1)

    return config if config else None
