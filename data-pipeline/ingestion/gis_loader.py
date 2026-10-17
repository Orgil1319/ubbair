"""
ingestion/gis_loader.py

scheduler.py-ийн дуудаж байгаа GISLoader class.

Бодит татах/боловсруулах логикийг (requests + geopandas + sqlalchemy)
ДАХИН БИЧЭЭГҮЙ - харин дата-pipeline/fetch_flood_zones.py-д аль хэдийн
сайн бичигдсэн SOURCES, fetch_data(), to_geojson_features(),
build_geodataframe(), _save_raw_backup() функцуудыг шууд дахин ашиглаж байна.

Энэ файл зөвхөн:
1. asyncpg pool-той ажиллах async interface өгдөг (scheduler.py-ийн
   бусад fetcher-үүдтэй (NKHBHGFetcher, PriceScraper) нийцүүлэхийн тулд).
2. Синхрон geopandas/sqlalchemy кодыг asyncio.to_thread()-ээр дамжуулж,
   event loop-ыг блоклохоос сэргийлдэг.
3. "Сард 1 удаа хийхэд хангалттай" throttling-ийг хэрэгжүүлдэг -
   scheduler 2 долоо хоног тутам дуудсан ч, GIS өгөгдөл бодитоор
   30 хоног тутамд л дахин татагдана.

АНХААР: Энэ модуль `from fetch_flood_zones import ...` гэж top-level
script-ээс импорт хийдэг. /app (data-pipeline) WORKDIR-аас scheduler.py
ажиллуулдаг тул энэ absolute import зөв ажиллана (fetch_flood_zones.py
яг /app/fetch_flood_zones.py байрлалтай байх ёстой).
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine

from fetch_flood_zones import (
    SOURCES,
    fetch_data,
    to_geojson_features,
    build_geodataframe,
    _save_raw_backup,
)

logger = logging.getLogger("gis_loader")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/realestate",
)

REFRESH_INTERVAL = timedelta(days=30)

def _build_sync_engine_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return database_url


class GISLoader:
    def __init__(self, db_pool):
        self.db_pool = db_pool
        # geopandas.to_postgis() синхрон тул тусдаа sqlalchemy engine хэрэгтэй
        # (db_pool бол asyncpg pool, geopandas-тай шууд ажиллахгүй).
        self._engine = create_engine(_build_sync_engine_url(DATABASE_URL))

    async def _ensure_metadata_table(self) -> None:
        """Давхарга бүрийг хамгийн сүүлд хэзээ шинэчилсэнийг хадгалах
        хүснэгт байгаа эсэхийг шалгаж, байхгүй бол үүсгэнэ."""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS gis_layers_metadata (
                    layer_name TEXT PRIMARY KEY,
                    last_fetched_at TIMESTAMPTZ
                )
                """
            )

    async def _get_last_fetched(self, layer_name: str):
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT last_fetched_at FROM gis_layers_metadata WHERE layer_name = $1",
                layer_name,
            )
            return row["last_fetched_at"] if row else None

    async def _mark_fetched(self, layer_name: str) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO gis_layers_metadata (layer_name, last_fetched_at)
                VALUES ($1, NOW())
                ON CONFLICT (layer_name)
                DO UPDATE SET last_fetched_at = NOW()
                """,
                layer_name,
            )

    def _ingest_source_sync(self, name: str, config: dict) -> int:
        """Синхрон хэсэг (requests -> geopandas -> PostGIS). fetch_flood_zones.py-
        гийн ингэст логикийг дахин ашиглаж байна, давхар бичихгүйн тулд.
        event loop-ыг блоклохоос сэргийлж энэ method-ийг зөвхөн
        asyncio.to_thread()-ээр дуудна."""
        raw = fetch_data(config["action"], config.get("params", {}))

        # ЮУ Ч БОЛОВСРУУЛАХААСАА ӨМНӨ raw өгөгдлийг хадгалах (precious data)
        _save_raw_backup(name, raw)

        features = to_geojson_features(raw, config["geometry_kind"])
        gdf = build_geodataframe(features)

        if gdf is None or gdf.empty:
            logger.warning(f"[{name}] Хүчинтэй геометр олдсонгүй, алгаслаа.")
            return 0

        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        else:
            gdf = gdf.to_crs("EPSG:4326")

        gdf["source"] = "manaikhoroo.ub.gov.mn"
        gdf["fetched_at"] = datetime.now(timezone.utc).isoformat()

        from sqlalchemy import text

        # 1. Geometry → WKT string
        gdf_copy = gdf.copy()
        gdf_copy["geometry"] = gdf_copy["geometry"].apply(lambda x: x.wkt if x else None)

        # 2. pandas.to_sql() нь pandas < 2.0 + SQLAlchemy >= 2.0 хослолд ажиллахгүй.
        #    SQLAlchemy core-оор шууд бичнэ.
        import pandas as pd
        cols = list(gdf_copy.columns)
        quoted_cols = ", ".join(f'"{c}"' for c in cols)
        col_defs    = ", ".join(f'"{c}" TEXT' for c in cols)
        params_sql  = ", ".join(f":p{i}" for i in range(len(cols)))

        clean = gdf_copy.where(pd.notnull(gdf_copy), other=None)
        records = [
            {f"p{i}": row[c] for i, c in enumerate(cols)}
            for row in clean.to_dict("records")
        ]

        geom_type = "POLYGON" if config["geometry_kind"] == "polygon" else "POINT"

        with self._engine.begin() as conn:
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

        return len(gdf)

    async def refresh_all(self) -> dict:
        """SOURCES-ийн БҮХ давхаргыг throttling-г үл харгалзан дахин татна.
        Гар аргаар бүрэн шинэчлэл хийх шаардлагатай бол ашиглана."""
        await self._ensure_metadata_table()
        results = {}

        for name, config in SOURCES.items():
            logger.info(f"[{name}] Татаж байна (refresh_all)...")
            try:
                count = await asyncio.to_thread(self._ingest_source_sync, name, config)
                await self._mark_fetched(name)
                results[name] = {"status": "ok", "count": count}
            except Exception as e:
                logger.error(f"[{name}] Алдаа гарлаа: {e}")
                results[name] = {"status": "error", "error": str(e)}

        return results

    async def refresh_if_needed(self) -> dict:
        """scheduler.py-ийн дуудаж байгаа гол method.

        Зөвхөн REFRESH_INTERVAL (30 хоног) хугацаа өнгөрсөн давхаргуудыг
        дахин татна. Бусдыг алгасна - тиймээс scheduler 2 долоо хоног
        тутам дуудсан ч, GIS өгөгдөл бодитоор сард 1 удаа л сүлжээ рүү
        хандана."""
        await self._ensure_metadata_table()
        results = {}
        now = datetime.now(timezone.utc)

        for name, config in SOURCES.items():
            last_fetched = await self._get_last_fetched(name)

            if last_fetched is not None and (now - last_fetched) < REFRESH_INTERVAL:
                logger.info(
                    f"[{name}] Сүүлд {last_fetched.isoformat()}-д шинэчилсэн, "
                    f"одоохондоо алгаслаа."
                )
                results[name] = {
                    "status": "skipped",
                    "last_fetched_at": last_fetched.isoformat(),
                }
                continue

            logger.info(f"[{name}] Шинэчлэх хугацаа болсон, татаж байна...")
            try:
                count = await asyncio.to_thread(self._ingest_source_sync, name, config)
                await self._mark_fetched(name)
                results[name] = {"status": "ok", "count": count}
            except Exception as e:
                logger.error(f"[{name}] Алдаа гарлаа: {e}")
                results[name] = {"status": "error", "error": str(e)}

        return results