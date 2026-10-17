import json
import logging
import re
import uuid
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URL = "postgresql://user:password@localhost:5432/realestate"


def extract_ad_id(url):
    if not url:
        return None
    match = re.search(r'/adv/(\d+)_', url)
    return match.group(1) if match else None


def make_uuid(ad_id: str) -> str:
    """ad_id-аас тогтмол UUID үүсгэх — дахин ажиллуулахад ижил UUID гарна"""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"unegui:{ad_id}"))


def parse_price(price_val, title):
    if price_val and price_val != 0:
        return int(price_val)
    if not title:
        return 0
    terbum = re.search(r'([\d\.]+)\s*[Тт]эрбум', title)
    say = re.search(r'([\d\.]+)\s*сая', title)
    if terbum:
        return int(float(terbum.group(1)) * 1_000_000_000)
    if say:
        return int(float(say.group(1)) * 1_000_000)
    return 0


def parse_area(area_str):
    if not area_str:
        return 0
    match = re.search(r'([\d\.]+)', str(area_str))
    return float(match.group(1)) if match else 0


def parse_rooms(rooms_str):
    if not rooms_str:
        return 0
    match = re.search(r'(\d+)', str(rooms_str))
    return int(match.group(1)) if match else 0


def parse_int(val):
    if not val:
        return 0
    match = re.search(r'(\d+)', str(val))
    return int(match.group(1)) if match else 0


def main():
    try:
        with open("unegui_listings.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error("unegui_listings.json файл олдсонгүй!")
        return

    logger.info(f"Нийт {len(data)} зар уншлаа")
    engine = create_engine(DB_URL)
    success = 0
    skipped = 0
    errors = 0

    with engine.begin() as conn:
        for item in data:
            lat = item.get("latitude")
            lng = item.get("longitude")
            if not lat or not lng:
                skipped += 1
                continue

            ad_id = item.get("ad_id") or extract_ad_id(item.get("url"))
            if not ad_id:
                skipped += 1
                continue

            property_uuid = make_uuid(str(ad_id))

            chars = item.get("characteristics", {})
            floor        = parse_int(chars.get("Хэдэн давхарт", "1")) or 1
            total_floors = parse_int(chars.get("Барилгын давхар", "1")) or 1
            built_year   = parse_int(chars.get("Ашиглалтанд орсон он", "0"))
            price        = parse_price(item.get("price"), item.get("title"))

            query = text("""
                INSERT INTO properties (
                    id, title, address, price, area_sqm, rooms,
                    floor, total_floors, build_year, property_type, developer_name,
                    permit_id, risk_level, source_url,
                    geom
                ) VALUES (
                    :id, :title, :address, :price, :area_sqm, :rooms,
                    :floor, :total_floors, :build_year, :property_type, :developer_name,
                    :permit_id, :risk_level, :source_url,
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
                )
                ON CONFLICT (id) DO UPDATE SET
                    price        = EXCLUDED.price,
                    area_sqm     = EXCLUDED.area_sqm,
                    floor        = EXCLUDED.floor,
                    total_floors = EXCLUDED.total_floors,
                    build_year   = EXCLUDED.build_year,
                    geom         = EXCLUDED.geom,
                    updated_at   = NOW()
            """)

            try:
                conn.execute(query, {
                    "id":             property_uuid,
                    "title":          item.get("title", ""),
                    "address":        item.get("location") or "",
                    "price":          price,
                    "area_sqm":       parse_area(chars.get("Талбай")),
                    "rooms":          parse_rooms(chars.get("Өрөөний тоо")),
                    "floor":          floor,
                    "total_floors":   total_floors,
                    "build_year":     built_year,
                    "property_type":  chars.get("Барилгын төрөл", "Apartment"),
                    "developer_name": "Unknown",
                    "permit_id":      None,
                    "risk_level":     "low",
                    "source_url":     item.get("url", ""),
                    "lat":            float(lat),
                    "lng":            float(lng),
                })
                success += 1
            except Exception as e:
                logger.error(f"Алдаа [{ad_id}]: {e}")
                errors += 1

    logger.info(f"✅ Амжилттай: {success} | ⏭ Алгасав: {skipped} | ❌ Алдаа: {errors}")


if __name__ == "__main__":
    main()