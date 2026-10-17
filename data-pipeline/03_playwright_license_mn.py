"""
Playwright ашиглан license.mn-ийн дата татах.

license.mn нь React SPA тул энгийн httpx/requests-р HTML-г авах боломжгүй.
Playwright нь бодит хөтөч ажиллуулж JavaScript-г render хийдэг.

Суулгах:
    pip install playwright
    playwright install chromium

Хэрэглэх:
    python 03_playwright_license_mn.py
"""

import asyncio
import json
import logging
from pathlib import Path
from playwright.async_api import async_playwright, Page, Request, Response

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("output/license_mn")

# Барилгын тусгай зөвшөөрлийн хуудасны URL-ууд
# (license.mn-д нэвтрэлгүйгээр харах боломжтой нийтийн хуудсууд)
TARGET_URLS = [
    "https://license.mn/",
    "https://license.mn/licenses",
    "https://license.mn/public/licenses",
    "https://license.mn/organizations",
]

# Барилгын тусгай зөвшөөрлийн хуудас
MCIS_GRANTS_URL = "https://mcis.gov.mn/mn/grants"


class APIInterceptor:
    """
    Playwright-р сайт нээхэд гарах API дуудалтуудыг тасалж,
    response дата-г хадгална.
    """

    def __init__(self):
        self.captured_responses: list[dict] = []
        self.captured_apis: list[str] = []

    def on_request(self, request: Request):
        url = request.url
        # JSON API дуудалтуудыг бүртгэнэ
        if any(kw in url for kw in ["/api/", "/v1/", "/licenses", "/grants"]):
            logger.info(f"  → API дуудалт: {request.method} {url}")
            self.captured_apis.append(url)

    async def on_response(self, response: Response):
        url = response.url
        content_type = response.headers.get("content-type", "")

        if "json" in content_type and any(
            kw in url for kw in ["/api/", "/licenses", "/grants", "/organizations"]
        ):
            try:
                body = await response.json()
                self.captured_responses.append({
                    "url": url,
                    "status": response.status,
                    "data": body,
                })
                logger.info(f"  ✓ JSON response: {url} ({response.status})")
            except Exception:
                pass


async def scrape_license_mn_with_playwright():
    """
    license.mn-г бодит хөтчөөр нээж:
    1. API дуудалтуудыг тасалж дата авна
    2. Харагдаж буй жагсаалтыг HTML-с parse хийнэ
    3. Хүчингүй болгосон компаниудын жагсаалт хайна
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    interceptor = APIInterceptor()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,  # False болговол хөтөч харагдана (debug-д тустай)
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="mn-MN",
        )
        page = await context.new_page()

        # API дуудалт тасалгааг идэвхжүүлнэ
        page.on("request", interceptor.on_request)
        page.on("response", lambda r: asyncio.ensure_future(interceptor.on_response(r)))

        all_data = []

        for url in TARGET_URLS:
            logger.info(f"\nНээж байна: {url}")
            try:
                await page.goto(url, wait_until="networkidle", timeout=20000)
                await asyncio.sleep(2)  # JS render хүлээнэ

                # Хуудасны агуулгыг авна
                content = await page.content()

                # Хүснэгтийн мөрүүд хайна
                rows = await extract_table_data(page)
                if rows:
                    all_data.extend(rows)
                    logger.info(f"  {len(rows)} мөр олдлоо")

                # Screenshot (debug-д тустай)
                screenshot_path = OUTPUT_DIR / f"screenshot_{url.replace('https://', '').replace('/', '_')}.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)

            except Exception as e:
                logger.error(f"  Алдаа: {e}")

        # Хүчингүй болгосон ТЗ хайх
        logger.info("\nХүчингүй болгосон тусгай зөвшөөрөл хайж байна...")
        invalid_data = await search_invalid_licenses(page)
        if invalid_data:
            all_data.extend(invalid_data)

        await browser.close()

    # Үр дүн хадгалах
    results = {
        "captured_apis": list(set(interceptor.captured_apis)),
        "api_responses": interceptor.captured_responses,
        "table_data": all_data,
    }

    out_path = OUTPUT_DIR / "license_mn_data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✅ Дууслаа:")
    logger.info(f"  API endpoint: {len(results['captured_apis'])} олдлоо")
    logger.info(f"  Хүснэгтийн мөр: {len(all_data)}")
    logger.info(f"  Хадгалсан: {out_path}")

    # Олдсон API-уудыг тусад нь хэвлэнэ
    if results["captured_apis"]:
        logger.info("\n=== ОЛДСОН API ENDPOINT-УУД ===")
        for api in results["captured_apis"]:
            logger.info(f"  {api}")
        logger.info("\nЭдгээрийг 02_mcis_license_scraper.py-д нэмж ашиглаж болно!")

    return results


async def extract_table_data(page: Page) -> list[dict]:
    """
    Хуудасны хүснэгтийн дата авна.
    """
    try:
        # Хүснэгт хайна
        tables = await page.query_selector_all("table")
        all_rows = []

        for table in tables:
            # Толгой мөр
            headers = []
            header_cells = await table.query_selector_all("th")
            for cell in header_cells:
                text = await cell.inner_text()
                headers.append(text.strip())

            if not headers:
                continue

            # Мэдээллийн мөрүүд
            body_rows = await table.query_selector_all("tbody tr")
            for row in body_rows:
                cells = await row.query_selector_all("td")
                if not cells:
                    continue
                row_data = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        text = await cell.inner_text()
                        row_data[headers[i]] = text.strip()
                if row_data:
                    all_rows.append(row_data)

        return all_rows
    except Exception as e:
        logger.debug(f"Хүснэгт авахад алдаа: {e}")
        return []


async def search_invalid_licenses(page: Page) -> list[dict]:
    """
    Хүчингүй болгосон тусгай зөвшөөрлийн жагсаалт хайна.
    "БҮАТЗ-ийг хүчингүй болгосон ААНБ-ын жагсаалт" холбоос хайж нээнэ.
    """
    try:
        # "хүчингүй" гэсэн текст бүхий холбоос хайна
        links = await page.query_selector_all("a")
        for link in links:
            text = await link.inner_text()
            if "хүчингүй" in text.lower() or "invalid" in text.lower():
                href = await link.get_attribute("href")
                logger.info(f"  Холбоос олдлоо: '{text}' → {href}")
                if href:
                    try:
                        await page.goto(href, wait_until="networkidle", timeout=15000)
                        await asyncio.sleep(2)
                        rows = await extract_table_data(page)
                        if rows:
                            return rows
                    except Exception as e:
                        logger.debug(f"  Хуудас нээхэд алдаа: {e}")
    except Exception as e:
        logger.debug(f"Хүчингүй ТЗ хайхад алдаа: {e}")
    return []


async def scrape_mcis_grants_page():
    """
    mcis.gov.mn/mn/grants хуудсаас тусгай зөвшөөрлийн
    жагсаалтын Excel файлуудын холбоосуудыг авна.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        logger.info(f"mcis.gov.mn grants хуудас нээж байна...")

        # Хуудас бүрийн download холбоосуудыг авна
        downloads = []

        page.on("download", lambda d: downloads.append(d))

        await page.goto(MCIS_GRANTS_URL, wait_until="networkidle", timeout=20000)
        await asyncio.sleep(2)

        # Excel / PDF холбоосууд
        links = await page.evaluate("""
            () => {
                const links = [];
                document.querySelectorAll('a[href]').forEach(a => {
                    const href = a.href;
                    const text = a.innerText.trim();
                    if (href.match(/\.(xlsx|xls|pdf|csv)$/i) || 
                        text.includes('Excel') || 
                        text.includes('татах') ||
                        text.includes('мэдээлэл')) {
                        links.push({ href, text });
                    }
                });
                return links;
            }
        """)

        logger.info(f"mcis.gov.mn-д {len(links)} файл холбоос олдлоо:")
        for link in links:
            logger.info(f"  {link['text']} → {link['href']}")

        out_path = OUTPUT_DIR / "mcis_grants_links.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(links, f, ensure_ascii=False, indent=2)

        await browser.close()
        return links


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "mcis":
        asyncio.run(scrape_mcis_grants_page())
    else:
        asyncio.run(scrape_license_mn_with_playwright())
