"""
mcud.gov.mn-с Барилгын тусгай зөвшөөрлийн мэдээллийг татах скрипт
=======================================================================
Стратеги:
1. mcud.gov.mn/a/{id} хуудсуудаас PDF/Excel файлын URL-уудыг олох
2. Файлуудыг татаж data-pipeline/output/ хавтсанд хадгалах
3. PDF-г опционоор parse хийх (pdfplumber ашиглан)

Мэдэгдэж буй нийтлэлийн ID-ууд (2026 оны байдлаар):
- /a/1725 — Барилгын ажил эрхлэх тусгай зөвшөөрөл (2026.01.30)
- /a/1726 — Зураг төсөл боловсруулах тусгай зөвшөөрөл (2026.01.30)
- /a/1746 — Хот байгуулалтын баримт бичиг боловсруулах зөвшөөрөл (2026.06)
"""

import os
import re
import json
import time
import logging
import requests
from pathlib import Path
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup
from datetime import datetime

# ── Logging тохиргоо ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Тохиргоо ─────────────────────────────────────────────────────────────────
BASE_URL = "https://mcud.gov.mn"
OUTPUT_DIR = Path(__file__).parent / "output" / "mcud_licenses"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# SSL баталгаажуулалтыг унтраах (mcud.gov.mn SSL сертификат асуудалтай)
VERIFY_SSL = False

# Татах нийтлэлийн ID-ууд (тусгай зөвшөөрлийн мэдээлэл)
LICENSE_ARTICLE_IDS = [
    {"id": 1725, "type": "construction_work", "desc": "Барилгын ажил эрхлэх тусгай зөвшөөрөл"},
    {"id": 1726, "type": "design", "desc": "Зураг төсөл боловсруулах тусгай зөвшөөрөл"},
    {"id": 1746, "type": "urban_planning", "desc": "Хот байгуулалтын зөвшөөрөл"},
]

# Мэдэгдэж буй PDF URL (a/1725 дотроос олдсон)
KNOWN_LICENSE_PDFS = [
    {
        "url": "https://mcud.gov.mn/resource/mcud/File/2026/03/26/gqju8nvr1l0cjzq5/%D0%91%D0%90%D0%A0%D0%98%D0%9B%D0%93%D0%90%20%D0%91%D0%90%D0%99%D0%93%D0%A3%D0%A3%D0%9B%D0%90%D0%9C%D0%96%202026.01.30-%D0%9D%D0%AB%20%D3%A8%D0%94%D0%A0%D0%98%D0%99%D0%9D%20%D0%91%D0%90%D0%99%D0%94%D0%9B%D0%90%D0%90%D0%A0%20OPENDATA%201%201.pdf",
        "type": "construction_work",
        "desc": "Барилгын ажил эрхлэх тусгай зөвшөөрөл 2026.01.30",
    }
]

# Нийтийн барилга / орон сууцны барилгын паспорт хуудсуудын ID
BUILDING_PASSPORT_PAGES = [
    # Орон сууцны барилга (дүүрэг тус бүрээр)
    {"id": 357, "district": "Баянгол", "type": "residential"},
    {"id": 358, "district": "Баянзүрх", "type": "residential"},
    {"id": 359, "district": "Сонгинохайрхан", "type": "residential"},
    {"id": 360, "district": "Сүхбаатар", "type": "residential"},
    {"id": 361, "district": "Хан-Уул", "type": "residential"},
    {"id": 362, "district": "Чингэлтэй", "type": "residential"},
    {"id": 363, "district": "Багахангай/Налайх/Багануур", "type": "residential"},
    # Олон нийтийн барилга
    {"id": 364, "district": "Баянгол", "type": "public"},
    {"id": 365, "district": "Баянзүрх", "type": "public"},
    {"id": 366, "district": "Сонгинохайрхан", "type": "public"},
    {"id": 367, "district": "Сүхбаатар", "type": "public"},
    {"id": 368, "district": "Хан-Уул", "type": "public"},
    {"id": 369, "district": "Чингэлтэй", "type": "public"},
    {"id": 370, "district": "Багахангай/Налайх/Багануур", "type": "public"},
]

# ── HTTP Session ──────────────────────────────────────────────────────────────
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "mn-MN,mn;q=0.9,en;q=0.8",
    "Referer": "https://mcud.gov.mn/",
})

# SSL анхааруулгыг дарах
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ── Тусламжийн функцүүд ───────────────────────────────────────────────────────
def safe_get(url: str, timeout: int = 30) -> requests.Response | None:
    """SSL алдааг тойрч GET хүсэлт илгээх."""
    try:
        resp = session.get(url, timeout=timeout, verify=VERIFY_SSL)
        resp.raise_for_status()
        return resp
    except requests.exceptions.SSLError:
        log.warning(f"SSL алдаа, verify=False дахин оролдож байна: {url}")
        try:
            resp = session.get(url, timeout=timeout, verify=False)
            resp.raise_for_status()
            return resp
        except Exception as e:
            log.error(f"HTTP алдаа {url}: {e}")
            return None
    except Exception as e:
        log.error(f"HTTP алдаа {url}: {e}")
        return None


def extract_file_links(html: str, base_url: str = BASE_URL) -> list[dict]:
    """HTML-с өгөгдлийн файлын холбоосуудыг (PDF, Excel) олох.
    Favicon, зураг, болон бусад хэрэггүй файлуудыг хассан.
    """
    # Зөвхөн өгөгдлийн файлын өргөтгөлүүд
    DATA_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".csv", ".docx", ".doc", ".zip"}
    # Хасах замын pattern-үүд
    SKIP_PATTERNS = {"favicon", "/resource/mcud/favicon/", "apple-touch", "manifest"}

    soup = BeautifulSoup(html, "html.parser")
    seen_urls = set()
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Favicon болон зургийн холбоосыг алгасах
        if any(skip in href.lower() for skip in SKIP_PATTERNS):
            continue

        full_url = urljoin(base_url, href)
        if full_url in seen_urls:
            continue

        text = a.get_text(strip=True)
        ext = Path(unquote(full_url).split("?")[0]).suffix.lower()

        if ext in DATA_EXTENSIONS:
            seen_urls.add(full_url)
            links.append({"url": full_url, "text": text, "extension": ext})

    return links


def download_file(url: str, dest_path: Path) -> bool:
    """Файлыг татаж хадгалах."""
    if dest_path.exists():
        log.info(f"Файл аль хэдийн байна, алгасаж байна: {dest_path.name}")
        return True

    log.info(f"Татаж байна: {url}")
    resp = safe_get(url)
    if resp is None:
        return False

    with open(dest_path, "wb") as f:
        f.write(resp.content)
    log.info(f"Хадгаллаа: {dest_path} ({len(resp.content) / 1024:.1f} KB)")
    return True


def scrape_article(article_id: int) -> dict:
    """mcud.gov.mn/a/{id} нийтлэлийн файлуудыг олж татах."""
    url = f"{BASE_URL}/a/{article_id}"
    log.info(f"Нийтлэл татаж байна: {url}")

    resp = safe_get(url)
    if resp is None:
        return {"article_id": article_id, "url": url, "files": [], "error": "HTTP алдаа"}

    links = extract_file_links(resp.text)
    log.info(f"  → {len(links)} файлын холбоос олдлоо")

    downloaded = []
    for link in links:
        filename = unquote(link["url"].split("/")[-1])
        # Хэт урт нэрийг богиносгох
        if len(filename) > 100:
            filename = f"article_{article_id}_{len(downloaded)}{link['extension']}"
        dest = OUTPUT_DIR / f"a{article_id}_{filename}"
        success = download_file(link["url"], dest)
        downloaded.append({**link, "saved_to": str(dest), "success": success})

    return {
        "article_id": article_id,
        "url": url,
        "scraped_at": datetime.now().isoformat(),
        "files": downloaded,
    }


def scrape_page(page_id: int, metadata: dict) -> dict:
    """mcud.gov.mn/p/{id} хуудасны агуулгыг татах (барилгын паспорт)."""
    url = f"{BASE_URL}/p/{page_id}"
    log.info(f"Хуудас татаж байна: {url} ({metadata.get('district','')}, {metadata.get('type','')})")

    resp = safe_get(url)
    if resp is None:
        return {"page_id": page_id, "url": url, "files": [], "error": "HTTP алдаа"}

    links = extract_file_links(resp.text)
    log.info(f"  → {len(links)} файлын холбоос олдлоо")

    district_slug = metadata.get("district", f"p{page_id}").replace("/", "_")
    btype = metadata.get("type", "unknown")

    downloaded = []
    for link in links:
        filename = unquote(link["url"].split("/")[-1])
        if len(filename) > 100:
            filename = f"p{page_id}_{len(downloaded)}{link['extension']}"
        dest = OUTPUT_DIR / f"passport_{btype}_{district_slug}_{filename}"
        success = download_file(link["url"], dest)
        downloaded.append({**link, "saved_to": str(dest), "success": success})

    return {
        "page_id": page_id,
        "url": url,
        "metadata": metadata,
        "scraped_at": datetime.now().isoformat(),
        "files": downloaded,
    }


def download_known_pdfs():
    """Урьдчилан мэдэгдэж буй PDF-уудыг шууд татах."""
    results = []
    for item in KNOWN_LICENSE_PDFS:
        filename = unquote(item["url"].split("/")[-1])
        if len(filename) > 100:
            filename = f"known_{item['type']}.pdf"
        dest = OUTPUT_DIR / filename
        success = download_file(item["url"], dest)
        results.append({**item, "saved_to": str(dest), "success": success})
    return results


def fetch_license_article_list() -> list[dict]:
    """
    mcud.gov.mn/p/c/40 — Тусгай зөвшөөрлийн хуудаснаас
    бүх нийтлэлийн холбоосуудыг олох.
    """
    url = f"{BASE_URL}/p/c/40"
    log.info(f"Тусгай зөвшөөрлийн жагсаалт татаж байна: {url}")

    resp = safe_get(url)
    if resp is None:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = []

    # Нийтлэлийн холбоосуудыг олох (/a/ path)
    for a in soup.find_all("a", href=re.compile(r"/a/\d+")):
        href = a["href"]
        article_id = int(re.search(r"/a/(\d+)", href).group(1))
        text = a.get_text(strip=True)
        # Тусгай зөвшөөрлийн холбоотой мэдээллийн нийтлэлүүдийг шүүх
        keywords = ["зөвшөөрөл", "тусгай", "барилга", "opendata", "хүчинтэй"]
        if any(kw in text.lower() for kw in keywords):
            articles.append({"id": article_id, "text": text, "url": f"{BASE_URL}/a/{article_id}"})

    log.info(f"  → {len(articles)} холбогдох нийтлэл олдлоо")
    return articles


# ── Үндсэн функц ──────────────────────────────────────────────────────────────
def main():
    log.info("=" * 60)
    log.info("MCUD.GOV.MN Тусгай зөвшөөрлийн scraper эхэллээ")
    log.info(f"Хадгалах хавтас: {OUTPUT_DIR}")
    log.info("=" * 60)

    results = {
        "scraped_at": datetime.now().isoformat(),
        "source": BASE_URL,
        "license_articles": [],
        "building_passports": [],
        "known_pdfs": [],
    }

    # 1. Мэдэгдэж буй PDF-уудыг шууд татах
    log.info("\n[1/4] Мэдэгдэж буй PDF файлуудыг татаж байна...")
    results["known_pdfs"] = download_known_pdfs()

    # 2. Тусгай зөвшөөрлийн нийтлэлийн жагсаалтыг татах
    log.info("\n[2/4] Тусгай зөвшөөрлийн нийтлэлүүдийн жагсаалтыг олж байна...")
    new_articles = fetch_license_article_list()

    # Мэдэгдэж буй болон шинэ нийтлэлүүдийг нэгтгэх
    all_article_ids = {a["id"] for a in LICENSE_ARTICLE_IDS}
    for art in new_articles:
        if art["id"] not in all_article_ids:
            LICENSE_ARTICLE_IDS.append({"id": art["id"], "type": "auto_found", "desc": art["text"][:80]})

    # 3. Тусгай зөвшөөрлийн нийтлэлүүдийг scrape хийх
    log.info(f"\n[3/4] {len(LICENSE_ARTICLE_IDS)} нийтлэлийг татаж байна...")
    for article in LICENSE_ARTICLE_IDS:
        result = scrape_article(article["id"])
        result["type"] = article.get("type")
        result["desc"] = article.get("desc")
        results["license_articles"].append(result)
        time.sleep(1)  # Сайтыг хэт их ачаалахгүйн тулд

    # 4. Барилгын паспортын хуудсуудыг scrape хийх
    log.info(f"\n[4/4] {len(BUILDING_PASSPORT_PAGES)} барилгын паспортын хуудсыг татаж байна...")
    for page in BUILDING_PASSPORT_PAGES:
        result = scrape_page(page["id"], page)
        results["building_passports"].append(result)
        time.sleep(0.5)

    # Үр дүнг JSON хэлбэрт хадгалах
    manifest_path = OUTPUT_DIR / "scrape_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Тоймлох
    log.info("\n" + "=" * 60)
    log.info("ДҮГНЭЛТ:")
    total_files = sum(
        len(a["files"]) for a in results["license_articles"]
    ) + sum(
        len(p["files"]) for p in results["building_passports"]
    ) + len(results["known_pdfs"])
    log.info(f"  Нийт файл: {total_files}")
    log.info(f"  Manifest:  {manifest_path}")
    log.info("=" * 60)

    return results


if __name__ == "__main__":
    main()
