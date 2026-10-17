"""
GIS үйлчилгээ.
PostGIS-ийн point-in-polygon query ашиглан байрны байршлаар
үер, хөрсний нуралт, газар хөдлөлтийн хагарлын бүсэд орох эсэхийг шалгана.
"""

import asyncpg
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class GISService:
    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool

    async def check_all_risks(self, lat: float, lng: float) -> dict:
        """
        Нэг байршлаар бүх GIS эрсдэлийг нэгэн зэрэг шалгана.
        """
        results = {}

        flood = await self.check_flood_zone(lat, lng)
        if flood:
            results["flood_zone"] = flood

        landslide = await self.check_landslide_zone(lat, lng)
        if landslide:
            results["landslide_zone"] = landslide

        earthquake = await self.check_earthquake_fault(lat, lng, buffer_meters=500)
        if earthquake:
            results["earthquake_fault"] = earthquake

        return results

    async def check_flood_zone(self, lat: float, lng: float) -> Optional[dict]:
        """
        ОБЕГ-ын үерийн бүсийн GIS давхаргаар шалгана.
        Бүсэд орвол түвшин болон хамрах нутгийн мэдээлэл буцаана.
        """
        query = """
            SELECT
                fz.zone_id,
                fz.risk_level,
                fz.area_name,
                fz.description_mn,
                fz.season,
                fz.updated_at
            FROM flood_zones fz
            WHERE ST_Contains(
                fz.geom,
                ST_SetSRID(ST_MakePoint($1, $2), 4326)
            )
            ORDER BY fz.risk_level DESC
            LIMIT 1
        """
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, lng, lat)
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Үерийн бүс шалгахад алдаа ({lat}, {lng}): {e}")
            return None

    async def check_landslide_zone(self, lat: float, lng: float) -> Optional[dict]:
        """
        Хөрсний нуралт, гулгалтын эрсдэлтэй бүсэд орох эсэх.
        """
        query = """
            SELECT
                lz.zone_id,
                lz.risk_level,
                lz.area_name,
                lz.slope_degree,
                lz.soil_type,
                lz.updated_at
            FROM landslide_zones lz
            WHERE ST_Contains(
                lz.geom,
                ST_SetSRID(ST_MakePoint($1, $2), 4326)
            )
            LIMIT 1
        """
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, lng, lat)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Хөрсний нуралт шалгахад алдаа: {e}")
            return None

    async def check_earthquake_fault(
        self, lat: float, lng: float, buffer_meters: int = 500
    ) -> Optional[dict]:
        """
        Газар хөдлөлтийн идэвхтэй хагарлаас buffer_meters зайд байгаа эсэх.
        """
        query = """
            SELECT
                ef.fault_id,
                ef.fault_name,
                ef.activity_level,
                ROUND(
                    ST_Distance(
                        ef.geom::geography,
                        ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography
                    )
                ) AS distance_meters
            FROM earthquake_faults ef
            WHERE ST_DWithin(
                ef.geom::geography,
                ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography,
                $3
            )
            ORDER BY distance_meters
            LIMIT 1
        """
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, lng, lat, buffer_meters)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Газар хөдлөлт шалгахад алдаа: {e}")
            return None

    async def get_district_risk_summary(self, district_name: str) -> dict:
        """
        Дүүрэг, хорооны нийт эрсдэлийн товч мэдээлэл.
        Үнийн зураглалд ашиглана.
        """
        query = """
            SELECT
                d.name_mn,
                COUNT(DISTINCT fz.zone_id) AS flood_zone_count,
                COUNT(DISTINCT lz.zone_id) AS landslide_zone_count,
                AVG(p.risk_score) AS avg_risk_score
            FROM districts d
            LEFT JOIN flood_zones fz ON ST_Intersects(d.geom, fz.geom)
            LEFT JOIN landslide_zones lz ON ST_Intersects(d.geom, lz.geom)
            LEFT JOIN properties p ON ST_Contains(d.geom, p.geom)
            WHERE d.name_mn = $1
            GROUP BY d.name_mn
        """
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, district_name)
                return dict(row) if row else {}
        except Exception as e:
            logger.error(f"Дүүргийн эрсдэл авахад алдаа: {e}")
            return {}
