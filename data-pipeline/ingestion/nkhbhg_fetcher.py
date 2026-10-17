"""
НХБХГ болон opendata.burtgel.gov.mn-ийн дата татах.
2 долоо хоног тутам автоматаар ажиллана.
Хар жагсаалт, зөвшөөрөлгүй барилга, ашиглалтад хүлээн аваагүй объектуудын
жагсаалтыг татаж мэдээллийн санд хадгална.
"""

import asyncio
import asyncpg
import httpx
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# opendata.burtgel.gov.mn-ийн API endpoint-ууд
# Барилга, газар, орон зайн өгөгдлийн бүлэг
OPENDATA_BASE = "https://opendata.burtgel.gov.mn/api"
OPENDATA_GOV = "https://opendata.gov.mn/api/3"

DATASETS = {
    "unauthorized_buildings": {
        "url": f"{OPENDATA_BASE}/buildings/unauthorized",
        "description": "Зөвшөөрөлгүй барилгуудын жагсаалт",
    },
    "not_accepted_buildings": {
        "url": f"{OPENDATA_BASE}/buildings/not-accepted",
        "description": "Ашиглалтад хүлээн аваагүй обьектуудын жагсаалт",
    },
    "blacklisted_companies": {
        "url": f"{OPENDATA_GOV}/action/datastore_search?resource_id=blacklist_companies",
        "description": "Хар жагсаалтын барилгын компаниуд",
    },
}


class NKHBHGFetcher:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_all(self) -> dict:
        """
        Бүх датасетийг татаж мэдээллийн санд хадгална.
        """
        results = {}
        for key, config in DATASETS.items():
            logger.info(f"Татаж байна: {config['description']}")
            try:
                count = await self._fetch_and_store(key, config["url"])
                results[key] = {"success": True, "count": count}
                logger.info(f"✓ {key}: {count} бичлэг хадгалагдлаа")
            except Exception as e:
                logger.error(f"✗ {key} татахад алдаа: {e}")
                results[key] = {"success": False, "error": str(e)}
        return results

    async def _fetch_and_store(self, dataset_key: str, url: str) -> int:
        """
        API-ээс дата татаж, тохирох хүснэгтэд хадгална.
        """
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()

        # opendata.gov.mn болон opendata.burtgel.gov.mn хоёр өөр формат ашиглана
        records = self._parse_response(data, dataset_key)

        if dataset_key == "blacklisted_companies":
            return await self._store_blacklist(records)
        elif dataset_key in ("unauthorized_buildings", "not_accepted_buildings"):
            return await self._store_building_status(records, dataset_key)
        return 0

    def _parse_response(self, data: dict, dataset_key: str) -> list[dict]:
        """
        API хариуны форматаас бичлэгүүдийг гаргана.
        """
        # opendata.gov.mn формат
        if "result" in data and "records" in data.get("result", {}):
            return data["result"]["records"]
        # opendata.burtgel.gov.mn формат
        if "data" in data:
            return data["data"]
        # Шууд массив
        if isinstance(data, list):
            return data
        logger.warning(f"Тодорхойгүй форматын хариу ({dataset_key}): {list(data.keys())}")
        return []

    async def _store_blacklist(self, records: list[dict]) -> int:
        """
        Хар жагсаалтын компаниудыг хадгална.
        normalized_name тооцоолж хурдан хайлтад бэлтгэнэ.
        """
        count = 0
        async with self.db.acquire() as conn:
            for record in records:
                company_name = (
                    record.get("company_name")
                    or record.get("COMPANY_NAME")
                    or record.get("name", "")
                ).strip()

                if not company_name:
                    continue

                normalized = self._normalize_company_name(company_name)

                await conn.execute(
                    """
                    INSERT INTO blacklisted_companies
                        (company_name, normalized_name, reason, source, blacklisted_date, updated_at)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    ON CONFLICT (normalized_name)
                    DO UPDATE SET
                        reason = EXCLUDED.reason,
                        updated_at = NOW()
                    """,
                    company_name,
                    normalized,
                    record.get("reason") or record.get("REASON", ""),
                    "НХБХГ / МХГ",
                    self._parse_date(record.get("date") or record.get("DATE")),
                )
                count += 1
        return count

    async def _store_building_status(self, records: list[dict], status_type: str) -> int:
        """
        Барилгын зөвшөөрлийн статусыг хадгална.
        """
        status = "unauthorized" if status_type == "unauthorized_buildings" else "not_accepted"
        count = 0
        async with self.db.acquire() as conn:
            for record in records:
                permit_id = record.get("permit_id") or record.get("PERMIT_ID", "")
                if not permit_id:
                    continue

                await conn.execute(
                    """
                    INSERT INTO building_permits
                        (permit_id, company_name, address, status, updated_at)
                    VALUES ($1, $2, $3, $4, NOW())
                    ON CONFLICT (permit_id)
                    DO UPDATE SET status = EXCLUDED.status, updated_at = NOW()
                    """,
                    str(permit_id),
                    record.get("company_name", ""),
                    record.get("address", ""),
                    status,
                )
                count += 1
        return count

    def _normalize_company_name(self, name: str) -> str:
        import re
        name = name.upper().strip()
        for suffix in [" ХХК", " ХК", " LLC", " LTD", " CO"]:
            name = name.replace(suffix, "")
        return re.sub(r'[^\w]', '', name)

    def _parse_date(self, date_str: Optional[str]):
        if not date_str:
            return None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except (ValueError, TypeError):
                continue
        return None

    async def close(self):
        await self.client.aclose()
