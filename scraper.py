# scraper.py
import sys
import asyncio
import json
import re
import urllib.parse
from datetime import datetime
from playwright.async_api import async_playwright

SEARCH_BASE = "https://indiankanoon.org/search/"

def parse_case_and_date(text: str):
    """
    Try to parse case title lines like:
    'Foo vs Bar on 10 December, 2025'
    Returns: case_name, day, month, year, iso_date
    """
    m = re.match(r"^(.*?)\s+on\s+(\d{1,2})\s+([A-Za-z]+),\s+(\d{4})$", text.strip())
    if not m:
        return None
    case_name = m.group(1).strip()
    day = int(m.group(2))
    month = m.group(3).strip()
    year = int(m.group(4))
    try:
        dt = datetime.strptime(f"{day} {month} {year}", "%d %B %Y").date()
        iso_date = dt.isoformat()
    except Exception:
        iso_date = None
    return case_name, day, month, year, iso_date

def doc_id_from_href(href: str):
    """Extract numeric doc id from /docfragment/<id>/... or /doc/<id>/..."""
    m = re.search(r"/docfragment/(\d+)", href) or re.search(r"/doc/(\d+)", href)
    return m.group(1) if m else None

def build_search_url(keyword: str) -> str:
    encoded_kw = urllib.parse.quote(keyword)
    form_input = f"{encoded_kw}++doctypes%3A+supremecourt+sortby%3Amostrecent"
    return f"{SEARCH_BASE}?formInput={form_input}"

async def scrape_keyword(keyword: str, max_links: int = 10, headless: bool = True):
    """
    Scrape Indian Kanoon for Supreme Court judgments matching a keyword.
    Returns list of dicts with fields aligned to DB schema.
    """
    url = build_search_url(keyword)
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")

        links = await page.query_selector_all("a")
        for a in links:
            text = (await a.inner_text()).strip()
            href = await a.get_attribute("href") or ""
            if not text or not href:
                continue

            # Skip "Full Document" links
            if text.lower() == "full document":
                continue

            if href.startswith("/docfragment") or href.startswith("/doc/"):
                doc_id = doc_id_from_href(href)
                if not doc_id:
                    continue
                full_link = f"https://indiankanoon.org/doc/{doc_id}/"

                record = {
                    "keyword": keyword,
                    "title": text,
                    "link": full_link,
                }

                parsed = parse_case_and_date(text)
                if parsed:
                    case_name, day, month, year, iso_date = parsed
                    record.update({
                        "case_name": case_name,
                        "day": day,
                        "month": month,
                        "year": year,
                        "judgment_date": iso_date,
                    })

                results.append(record)
                if len(results) >= max_links:
                    break


        await browser.close()

    return results

# CLI entry point for subprocess calls
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps([]))
        sys.exit(0)
    keyword = sys.argv[1]
    max_links = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    headless = bool(int(sys.argv[3])) if len(sys.argv) > 3 else True
    records = asyncio.run(scrape_keyword(keyword, max_links=max_links, headless=headless))
    print(json.dumps(records))