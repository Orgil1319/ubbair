"""
GIS өгөгдөл татах script - manaikhoroo.ub.gov.mn эх сурвалжаас.

Хуучин fetch_flood_zones.py-г өргөтгөж, нэг л script-оор олон төрлийн
давхарга (flood zones, schools, kindergartens, hospitals, г.м.) татах
боломжтой болгосон.

ЧУХАЛ ӨӨРЧЛӨЛТ:
1. Боловсруулахаасаа ӨМНӨ raw response-ийг timestamp-тэй файл болгож
   data/raw/ дотор хадгалдаг - хуучин сайн өгөгдөл дарагдахгүй.
2. SOURCES dict-д шинэ давхарга нэмэхэд зөвхөн нэг entry нэмэхэд хангалттай.
3. addMarkerDistrict endpoint-ийн бодит response бүтэц:
   {"marker": [["lat_str", "lng_str"], ...]} - dict (list биш!),
   координат хосуудын массив, properties дагалддаггүй.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import geopandas as gpd
import requests
from shapely.geometry import shape
from sqlalchemy import create_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://manaikhoroo.ub.gov.mn"
HEADERS = {
    "Referer": f"{BASE_URL}/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

RAW_DATA_DIR = Path("data/raw")
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_URL = os.environ.get(
    "GIS_INGEST_DB_URL",
    os.environ.get(
        "DATABASE_URL", 
        "postgresql://user:password@localhost:5432/realestate"
    )
)

SOURCES = {
    "flood_risk_zones": {
        "action": "risksBorder",
        "params": {},
        "geometry_kind": "polygon",
    },
    "kindergartens": {
        "action": "addMarkerDistrict",
        "params": {"type": 3},
        "geometry_kind": "point",
    },
    "schools": {
        "action": "addMarkerDistrict",
        "params": {"type": 4},
        "geometry_kind": "point",
    },
    "hospitals": {
        "action": "getKmlType",
        "params": {"type": 44},
        # TODO: type=44 нь "no_data" буцааж байна - энэ бодит endpoint биш
        # байж магадгүй. Network tab-аар addMarkerDistrict хувилбарыг
        # шалгаж шаардлагатай бол энд солих.
        "geometry_kind": "point",
    },
}


def _save_raw_backup(name: str, payload) -> Path:
    """Эх сурвалжаас ирсэн RAW өгөгдлийг ямар нэг боловсруулалт хийхээс
    ӨМНӨ диск рүү хадгална. Файлын нэрэнд timestamp орсон тул хэзээ ч
    дарагдахгүй - боловсруулалт алдаатай болсон ч эх өгөгдөл хадгалагдана."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RAW_DATA_DIR / f"{name}_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        # Хэрэв payload нь string (KML/"no_data") байвал шууд бичнэ
        if isinstance(payload, str):
            f.write(payload)
        else:
            json.dump(payload, f, ensure_ascii=False)
    logger.info(f"  RAW backup хадгаллав: {path}")
    return path


def fetch_data(action: str, params: dict):
    url = f"{BASE_URL}/index.php"
    query = {"action": action, **params}
    # verify=False - .mn government domain-уудаас заримдаа SSL chain
    # асуудал гарах тул bypass хийсэн.
    resp = requests.get(url, params=query, headers=HEADERS, timeout=30, verify=False)
    resp.raise_for_status()

    try:
        return resp.json()
    except requests.exceptions.JSONDecodeError:
        # Хэрэв endpoint JSON биш текст ("no_data" эсвэл KML) буцаадаг бол
        logger.warning(f"Response is not JSON for {action}. Storing as raw text.")
        return resp.text


def to_geojson_features(raw_data, geometry_kind: str) -> list:
    features = []

    if isinstance(raw_data, str):
        # XML/KML эсвэл "no_data" гэх мэт текст хариу
        if raw_data.strip().lower() == "no_data":
            logger.warning("Эх сурвалж 'no_data' буцаалаа - энэ type/action-д өгөгдөл байхгүй.")
        else:
            logger.error("Cannot parse raw string/XML directly into JSON features. Returning empty list.")
        return features

    # manaikhoroo.ub.gov.mn-ийн addMarkerDistrict endpoint-ийн бодит формат:
    # {"marker": [["lat_str", "lng_str"], ["lat_str", "lng_str"], ...]}
    # Координат хосуудын массив, нэр/properties дагалддаггүй.
    if isinstance(raw_data, dict) and "marker" in raw_data and "info" in raw_data:
        markers = raw_data["marker"]
        infos = raw_data["info"]
        if isinstance(markers, list) and isinstance(infos, list):
            for i in range(min(len(markers), len(infos))):
                pair = markers[i]
                info = infos[i]
                if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                    continue
                try:
                    lat, lng = float(pair[0]), float(pair[1])
                except (TypeError, ValueError):
                    continue
                    
                name = info[0] if info and len(info) > 0 else "Unknown"
                
                features.append(
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [lng, lat]},
                        "properties": {"name": name},
                    }
                )
        return features

    if not isinstance(raw_data, list):
        logger.warning(f"Тодорхойгүй response бүтэц: {type(raw_data)}. Хоосон жагсаалт буцаав.")
        return features

    for item in raw_data:
        if geometry_kind == "polygon":
            # risksBorder маягийн endpoint-ийн item бүр аль хэдийн
            # "geometry" талбайтай ирдэг гэж үзнэ.
            if isinstance(item, dict) and "geometry" in item:
                features.append(item)
            continue

        # geometry_kind == "point" (fallback - бусад боломжит формат)
        if not isinstance(item, dict):
            continue

        lat = item.get("lat") or item.get("latitude") or item.get("y")
        lng = item.get("lng") or item.get("longitude") or item.get("x")
        if lat is None or lng is None:
            continue

        try:
            lat, lng = float(lat), float(lng)
        except (TypeError, ValueError):
            continue

        properties = {
            k: v
            for k, v in item.items()
            if k not in ("lat", "lng", "latitude", "longitude", "x", "y")
        }

        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lng, lat]},
                "properties": properties,
            }
        )

    return features


def build_geodataframe(features: list) -> Optional[gpd.GeoDataFrame]:
    valid_features = []
    for f in features:
        try:
            geom = f.get("geometry")
            if not geom or not geom.get("coordinates"):
                continue
            s = shape(geom)
            if s.is_valid:
                valid_features.append(f)
        except Exception:
            continue

    if not valid_features:
        return None

    gdf = gpd.GeoDataFrame.from_features(valid_features, crs="EPSG:4326")
    if "id" in gdf.columns:
        gdf = gdf.rename(columns={"id": "source_id"})
    return gdf


def ingest_source(name: str, config: dict, engine) -> None:
    logger.info(f"[{name}] Эх сурвалжаас өгөгдөл татаж байна...")

    raw = fetch_data(config["action"], config.get("params", {}))
    logger.info(f"[{name}] Татагдсан өгөгдлийн урт: {len(raw)}")

    _save_raw_backup(name, raw)

    features = to_geojson_features(raw, config["geometry_kind"])
    logger.info(f"[{name}] Ашиглаж болохуйц feature тоо: {len(features)}")

    gdf = build_geodataframe(features)
    if gdf is None or gdf.empty:
        logger.warning(f"[{name}] Хүчинтэй геометр олдсонгүй, алгаслаа.")
        return

    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    else:
        gdf = gdf.to_crs("EPSG:4326")

    gdf["source"] = "manaikhoroo.ub.gov.mn"
    gdf["fetched_at"] = datetime.now(timezone.utc).isoformat()

    from sqlalchemy import text
    import pandas as pd

    logger.info(f"[{name}] PostGIS руу оруулж байна (SQLAlchemy core)...")

    # 1. Geometry → WKT string (geoalchemy2 / psycopg driver issue-аас зайлсхийхийн тулд)
    gdf_copy = gdf.copy()
    gdf_copy["geometry"] = gdf_copy["geometry"].apply(lambda x: x.wkt if x else None)

    # 2. pandas.to_sql() нь pandas < 2.0 + SQLAlchemy >= 2.0 хослолд ажиллахгүй
    #    Хамааралгүй байхын тулд SQLAlchemy core-оор шууд бичнэ.
    cols = list(gdf_copy.columns)
    quoted_cols = ", ".join(f'"{c}"' for c in cols)
    col_defs    = ", ".join(f'"{c}" TEXT' for c in cols)
    params_sql  = ", ".join(f":p{i}" for i in range(len(cols)))

    # NaN → None (PostgreSQL NULL-тай нийцүүлэхийн тулд)
    clean = gdf_copy.where(pd.notnull(gdf_copy), other=None)
    records = [
        {f"p{i}": row[c] for i, c in enumerate(cols)}
        for row in clean.to_dict("records")
    ]

    geom_type = "POLYGON" if config["geometry_kind"] == "polygon" else "POINT"

    with engine.begin() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{name}"'))
        conn.execute(text(f'CREATE TABLE "{name}" ({col_defs})'))
        if records:
            conn.execute(
                text(f'INSERT INTO "{name}" ({quoted_cols}) VALUES ({params_sql})'),
                records,
            )
        conn.execute(text(
            f'ALTER TABLE "{name}" ALTER COLUMN geometry '
            f'TYPE geometry({geom_type}, 4326) '
            f'USING ST_SetSRID(geometry::geometry, 4326)'
        ))

    logger.info(f"[{name}] {len(gdf)} объект '{name}' хүснэгтэд амжилттай орлоо.\n")


def main():
    engine = create_engine(DB_URL)
    for name, config in SOURCES.items():
        try:
            ingest_source(name, config, engine)
        except Exception as e:
            logger.error(f"[{name}] Алдаа гарлаа: {e}")
            continue


if __name__ == "__main__":
    main()