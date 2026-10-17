"""
mcis.gov.mn / license.mcis.gov.mn — Барилгын тусгай зөвшөөрлийн жагсаалт scraping.

Тайлбар:
  mcis.gov.mn нь тусгай зөвшөөрлийн жагсаалтыг нийтэд харуулдаг.
  license.mn нь React SPA тул шууд HTML parse хийх боломжгүй —
  арын API endpoint-уудыг ашиглах шаардлагатай.

Стратеги:
  1. mcis.gov.mn-ийн нийтийн хуудсаас Excel/PDF жагсаалт шууд татна
  2. license.mn-ийн API endpoint-уудыг Chrome DevTools-р олж ашиглана
  3. Олдохгүй бол Playwright/Selenium-р JS render хийнэ
"""

import httpx
import asyncio
import logging
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("output/mcis")

MCIS_BASE = "https://mcis.gov.mn"

# mcis.gov.mn-ийн нийтийн хуудасны тусгай зөвшөөрлийн жагсаалтын холбоосууд
# (Эдгээр нь хуудасны "Тусгай зөвшөөрөл" цэсэнд байдаг Excel файлууд)
KNOWN_EXCEL_LINKS = [
    # Барилгын ажил гүйцэтгэх ТЗ-тэй ААНБ
    f"{MCIS_BASE}/mn/grants",
    # Зураг төслийн ТЗ-тэй ААНБ
    f"{MCIS_BASE}/main/grants",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "mn-MN,mn;q=0.9,en;q=0.8",
    "Referer": "https://mcis.gov.mn/",
}


async def scrape_license_list_page(client: httpx.AsyncClient, url: str) -> list[dict]:
    """
    mcis.gov.mn-ийн тусгай зөвшөөрлийн хуудсаас
    Excel/PDF файлын холбоосуудыг олно.
    """
    try:
        resp = await client.get(url, headers=HEADERS)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP {e.response.status_code}: {url}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    file_links = []

    # Excel болон PDF холбоос хайх
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)

        # Excel / PDF файлын холбоос
        if any(ext in href.lower() for ext in [".xlsx", ".xls", ".pdf", ".csv"]):
            full_url = href if href.startswith("http") else f"{MCIS_BASE}{href}"
            file_links.append({
                "url": full_url,
                "name": text or Path(href).name,
                "type": "excel" if ".xls" in href.lower() else "pdf",
            })
            logger.info(f"  Файл олдлоо: {text} → {full_url}")

    return file_links


async def try_license_mn_api(client: httpx.AsyncClient) -> list[dict]:
    """
    license.mn нь React SPA (JavaScript-р рендердэг) тул
    шууд HTML parse хийх боломжгүй.

    Арын API endpoint-уудыг Chrome DevTools → Network tab-аар олох аргачлал:
    1. Chrome-д license.mn нээнэ
    2. F12 → Network → XHR/Fetch шүүнэ
    3. "барилга" хайлт хийхэд гарах API дуудалтыг харна
    4. Олсон endpoint-ийг доор нэмнэ

    Доор нийтлэг pattern-уудыг туршиж үзнэ:
    """
    candidate_endpoints = [
        "https://license.mn/api/licenses",
        "https://license.mn/api/v1/licenses",
        "https://license.mn/api/public/licenses",
        "https://api.license.mn/licenses",
        "https://license.mn/api/organizations",
        # mcis.gov.mn-ийн API
        "https://mcis.gov.mn/api/grants",
        "https://mcis.gov.mn/api/v1/grants",
    ]

    working_endpoints = []
    for ep in candidate_endpoints:
        try:
            resp = await client.get(ep, headers=HEADERS, timeout=10.0)
            if resp.status_code == 200:
                content_type = resp.headers.get("content-type", "")
                if "json" in content_type:
                    logger.info(f"✓ API endpoint олдлоо: {ep}")
                    working_endpoints.append({
                        "url": ep,
                        "sample": resp.json() if len(resp.content) < 10000 else "large response",
                    })
            else:
                logger.debug(f"  {ep} → {resp.status_code}")
        except Exception as e:
            logger.debug(f"  {ep} → алдаа: {e}")
        await asyncio.sleep(0.5)

    return working_endpoints


async def download_file(client: httpx.AsyncClient, url: str, out_path: Path) -> bool:
    """
    Файл татаж хадгална.
    """
    if out_path.exists():
        logger.info(f"  Аль хэдийн байна: {out_path.name}")
        return True

    try:
        async with client.stream("GET", url, headers=HEADERS) as resp:
            resp.raise_for_status()
            with open(out_path, "wb") as f:
                async for chunk in resp.aiter_bytes(8192):
                    f.write(chunk)
        size_kb = out_path.stat().st_size // 1024
        logger.info(f"  ✓ {out_path.name} ({size_kb} KB)")
        return True
    except Exception as e:
        logger.error(f"  ✗ {out_path.name}: {e}")
        return False


async def parse_excel_to_blacklist(excel_path: Path) -> list[dict]:
    """
    Татсан Excel файлаас хар жагсаалтын мэдээлэл гаргана.
    """
    try:
        import openpyxl
    except ImportError:
        logger.warning("openpyxl суулгаагүй: pip install openpyxl")
        return []

    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    # Толгой мөр тодорхойлох
    header = [str(c).strip() if c else "" for c in rows[0]]
    logger.info(f"  Баганууд: {header}")

    records = []
    for row in rows[1:]:
        if not any(row):
            continue
        record = {}
        for i, col in enumerate(header):
            if i < len(row):
                record[col] = row[i]
        records.append(record)

    logger.info(f"  {len(records)} бичлэг олдлоо")
    return records


async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
    ) as client:

        logger.info("=== 1. license.mn API endpoint хайж байна ===")
        apis = await try_license_mn_api(client)
        if apis:
            api_path = OUTPUT_DIR / "found_apis.json"
            with open(api_path, "w", encoding="utf-8") as f:
                json.dump(apis, f, ensure_ascii=False, indent=2)
            logger.info(f"API мэдээлэл хадгалагдлаа: {api_path}")
        else:
            logger.warning("Нийтийн API endpoint олдсонгүй — Excel жагсаалт руу шилжинэ")

        logger.info("\n=== 2. mcis.gov.mn-ийн Excel жагсаалт хайж байна ===")
        all_files = []
        for url in KNOWN_EXCEL_LINKS:
            logger.info(f"Хуудас уншиж байна: {url}")
            files = await scrape_license_list_page(client, url)
            all_files.extend(files)
            await asyncio.sleep(1)

        logger.info(f"\nНийт {len(all_files)} файл олдлоо")

        logger.info("\n=== 3. Файлуудыг татаж байна ===")
        blacklist_records = []
        for file_info in all_files:
            safe_name = re.sub(r'[^\w.]', '_', file_info["name"])[:80]
            ext = "xlsx" if file_info["type"] == "excel" else "pdf"
            out_path = OUTPUT_DIR / f"{safe_name}.{ext}"

            success = await download_file(client, file_info["url"], out_path)

            if success and file_info["type"] == "excel":
                records = await parse_excel_to_blacklist(out_path)
                blacklist_records.extend(records)
            await asyncio.sleep(0.5)

        if blacklist_records:
            out_json = OUTPUT_DIR / "blacklist_companies.json"
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(blacklist_records, f, ensure_ascii=False, indent=2)
            logger.info(f"\n✅ Хар жагсаалт: {len(blacklist_records)} компани → {out_json}")

        # Дараагийн алхам заавар
        logger.info("""
=== ДАРААГИЙН АЛХАМУУД ===

Хэрэв license.mn API олдсонгүй бол:

1. PLAYWRIGHT АШИГЛАХ (JavaScript render хийх):
   pip install playwright
   playwright install chromium
   
   Дараа нь playwright_scraper.py-г ажиллуулна.

2. CHROME DEVTOOLS-Р API ОЛОХ:
   a) Chrome-д https://license.mn нээнэ
   b) F12 → Network → Fetch/XHR
   c) Тусгай зөвшөөрлийн жагсаалт хуудас нээхэд
      гарах API дуудалтыг харна
   d) Request URL-ийг копи хийж энэ файлд нэмнэ
   
3. БАЙГУУЛЛАГАД ХАНДАХ:
   МБҮА (Монголын барилгын үндэсний ассоциаци)
   Утас: 70111515
   Жил бүрийн хүчингүй болгосон ТЗ-ийн Excel жагсаалтыг
   шууд авах хүсэлт гаргах.
""")


if __name__ == "__main__":
    asyncio.run(main())
