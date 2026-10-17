import re
import time
import json
import random
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.unegui.mn"
LISTING_PATH = "/l-hdlh/l-hdlh-zarna/oron-suuts-zarna/"
REQUEST_DELAY = (2, 4)
MAX_PAGES = 2

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "mn-MN,mn;q=0.9,en;q=0.8",
}

session = requests.Session()
session.headers.update(HEADERS)

AD_LINK_RE  = re.compile(r"/adv/(\d+)_[^/\"'?#]+/")
GEO_RE      = re.compile(r'data-default-lat="([\d.]+)"\s+data-default-lng="([\d.]+)"')
PRICE_RE    = re.compile(r"[YУ]нэ\s*:\s*([\d']+)\s*₮", re.IGNORECASE)
VIEWS_RE    = re.compile(r"Үзсэн\s*:\s*(\d+)")
POSTED_RE   = re.compile(r"Нийтэлсэн\s*:\s*([^<\n]+)")
LOCATION_RE = re.compile(r"Байршил\s*:\s*([^<\n]+)")
AD_NUMBER_RE = re.compile(r"Зарын дугаар\s*:\s*(\d+)")
CHAR_LINE_RE = re.compile(r"^([\w\sА-Яа-яёӨөҮү]{2,40}):\s*(.{1,80})$")


def get_listing_links(page: int) -> list[str]:
    """Нэг хуудасны зарын давхардалгүй линкүүдийг буцаана."""
    url = f"{BASE_URL}{LISTING_PATH}?page={page}"
    resp = session.get(url, timeout=15)
    resp.raise_for_status()

    seen = set()
    links = []
    for m in AD_LINK_RE.finditer(resp.text):
        full = BASE_URL + m.group(0)
        if full not in seen:
            seen.add(full)
            links.append(full)
    return links


def parse_listing(url: str) -> dict:
    """Нэг зарын дэлгэрэнгүй хуудаснаас бүтэцтэй мэдээлэл задлана."""
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # --- Meta tag-аас гарчиг ---
    og_title = soup.find("meta", attrs={"property": "og:title"})
    title = og_title["content"].strip() if og_title else None

    # --- Үнэ ---
    price_match = PRICE_RE.search(html)
    price = int(price_match.group(1).replace("'", "")) if price_match else None

    # --- Координат: data-default-lat / data-default-lng ---
    geo_match = GEO_RE.search(html)
    if geo_match:
        latitude  = float(geo_match.group(1))
        longitude = float(geo_match.group(2))
    else:
        latitude = longitude = None

    # --- Байршил, огноо, ID, үзсэн тоо ---
    location_match = LOCATION_RE.search(html)
    location = location_match.group(1).strip() if location_match else None

    posted_match = POSTED_RE.search(html)
    posted_at = posted_match.group(1).strip() if posted_match else None

    ad_id_match = AD_NUMBER_RE.search(html)
    ad_id = ad_id_match.group(1) if ad_id_match else None

    views_match = VIEWS_RE.search(html)
    views = int(views_match.group(1)) if views_match else None

    # --- Шинж чанарууд (Key: Value) ---
    characteristics = {}
    for li in soup.find_all("li"):
        text = li.get_text(" ", strip=True)
        m = CHAR_LINE_RE.match(text)
        if m:
            key, val = m.group(1).strip(), m.group(2).strip()
            characteristics[key] = val

    return {
        "url":             url,
        "ad_id":           ad_id,
        "title":           title,
        "price":           price,
        "currency":        "MNT",
        "location":        location,
        "longitude":       longitude,
        "latitude":        latitude,
        "posted_at":       posted_at,
        "views":           views,
        "characteristics": characteristics,
    }


def main():
    all_listings = []

    for page in range(1, MAX_PAGES + 1):
        print(f"Хуудас {page} татаж байна...")
        try:
            links = get_listing_links(page)
        except requests.RequestException as e:
            print(f"  Хуудас татахад алдаа: {e}")
            break

        if not links:
            print("Цаашид зар олдсонгүй, зогсоно.")
            break

        for link in links:
            try:
                data = parse_listing(link)
                all_listings.append(data)
                print(f"  -> [{data['ad_id']}] {data['title']} | {data['price']}₮ | {data['location']}")
            except Exception as e:
                print(f"  Алдаа гарлаа ({link}): {e}")

            time.sleep(random.uniform(*REQUEST_DELAY))

        time.sleep(random.uniform(*REQUEST_DELAY))

    with open("unegui_listings.json", "w", encoding="utf-8") as f:
        json.dump(all_listings, f, ensure_ascii=False, indent=2)

    print(f"\nНийт {len(all_listings)} зар хадгаллаа -> unegui_listings.json")


if __name__ == "__main__":
    main()