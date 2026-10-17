import json
import os
import sys
from pathlib import Path

import psycopg

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

MIGRATIONS_DIR = Path(os.environ.get("MIGRATIONS_DIR", str(HERE.parent / "database" / "migrations")))
ALREADY_APPLIED = (
    psycopg.errors.DuplicateTable,
    psycopg.errors.DuplicateObject,
    psycopg.errors.DuplicateColumn,
)

from load_unegui_to_db import (
    extract_ad_id,
    make_uuid,
    parse_area,
    parse_int,
    parse_price,
    parse_rooms,
)


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "postgresql://realestate:realestate@localhost:5432/realestate")
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://"):
        url = url.replace(prefix, "postgresql://")
    return url


def apply_migrations(conn) -> list:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ DEFAULT NOW())"
    )
    conn.commit()
    done = {row[0] for row in conn.execute("SELECT filename FROM schema_migrations").fetchall()}
    applied = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name in done:
            continue
        try:
            conn.execute(path.read_text(encoding="utf-8"))
            applied.append(path.name)
        except ALREADY_APPLIED:
            conn.rollback()
        conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s) ON CONFLICT DO NOTHING", (path.name,))
        conn.commit()
    return applied


def seed_properties(conn) -> int:
    path = HERE / "unegui_listings.json"
    if not path.exists():
        return 0
    items = json.loads(path.read_text(encoding="utf-8"))
    inserted = 0
    with conn.cursor() as cur:
        for item in items:
            lat, lng = item.get("latitude"), item.get("longitude")
            ad_id = item.get("ad_id") or extract_ad_id(item.get("url"))
            if not lat or not lng or not ad_id:
                continue
            chars = item.get("characteristics", {})
            cur.execute(
                """
                INSERT INTO properties (
                    id, title, address, price, area_sqm, rooms, floor, total_floors,
                    build_year, property_type, developer_name, risk_level, source_url, geom
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'low', %s,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                )
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    make_uuid(str(ad_id)),
                    item.get("title", ""),
                    item.get("location") or "",
                    parse_price(item.get("price"), item.get("title")),
                    parse_area(chars.get("Талбай")),
                    parse_rooms(chars.get("Өрөөний тоо")),
                    parse_int(chars.get("Хэдэн давхарт", "1")) or 1,
                    parse_int(chars.get("Барилгын давхар", "1")) or 1,
                    parse_int(chars.get("Ашиглалтанд орсон он", "0")),
                    chars.get("Барилгын төрөл", "Apartment"),
                    "Unknown",
                    item.get("url", ""),
                    float(lng),
                    float(lat),
                ),
            )
            inserted += cur.rowcount
    return inserted


def seed_flood_zones(conn) -> int:
    path = HERE / "flood_risk_zones_ulaanbaatar.geojson"
    if not path.exists():
        return 0
    features = json.loads(path.read_text(encoding="utf-8")).get("features", [])
    inserted = 0
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS flood_risk_zones (
                id        INTEGER PRIMARY KEY,
                title     TEXT,
                year      INTEGER,
                area      DOUBLE PRECISION,
                geometry  GEOMETRY(Geometry, 4326) NOT NULL
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_flood_risk_zones_geom ON flood_risk_zones USING GIST(geometry)")
        for feature in features:
            props = feature.get("properties") or {}
            geometry = feature.get("geometry")
            if not geometry or props.get("id") is None:
                continue
            cur.execute(
                """
                INSERT INTO flood_risk_zones (id, title, year, area, geometry)
                VALUES (%s, %s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    int(props["id"]),
                    str(props.get("title") or ""),
                    parse_int(props.get("year")) or None,
                    float(props["area"]) if props.get("area") else None,
                    json.dumps(geometry),
                ),
            )
            inserted += cur.rowcount
        cur.execute("SELECT COUNT(*) FROM flood_zones")
        if cur.fetchone()[0] == 0:
            cur.execute(
                """
                INSERT INTO flood_zones (area_name, risk_level, description_mn, geom, source)
                SELECT
                    'Үерийн эрсдэлтэй бүс №' || id,
                    'medium',
                    'Үерийн эрсдэлтэй бүс (' || COALESCE(year::text, 'он тодорхойгүй') || ')',
                    ST_Multi(ST_MakeValid(geometry))::geometry(MultiPolygon, 4326),
                    'manaikhoroo.ub.gov.mn'
                FROM flood_risk_zones
                WHERE GeometryType(ST_Multi(ST_MakeValid(geometry))) = 'MULTIPOLYGON'
                """
            )
        cur.execute(
            """
            UPDATE properties p
               SET risk_level = 'medium'
             WHERE p.risk_level = 'low'
               AND EXISTS (SELECT 1 FROM flood_zones fz WHERE ST_Contains(fz.geom, p.geom::geometry))
            """
        )
    return inserted


def main() -> None:
    with psycopg.connect(database_url(), autocommit=False) as conn:
        migrations = apply_migrations(conn)
        properties = seed_properties(conn)
        zones = seed_flood_zones(conn)
        conn.commit()
    print(f"migrations: {', '.join(migrations) or 'шинэ зүйлгүй'}")
    print(f"seed: {properties} шинэ байр, {zones} шинэ үерийн бүс нэмэгдлээ")


if __name__ == "__main__":
    main()
