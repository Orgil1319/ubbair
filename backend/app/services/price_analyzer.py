"""
Үнийн шинжилгээ.
unegui.mn болон кадастрын мэдээлэлтэй харьцуулж
байрны үнэ хөөсөрсөн эсэхийг тодорхойлно.
"""

import json
import logging
from typing import Optional
import redis.asyncio as aioredis
from app.config import settings

logger = logging.getLogger(__name__)

# Дүүрэг бүрийн хүрэн коэффициент (байршлын нэмэлт)
DISTRICT_PREMIUM = {
    "Баянзүрх":   1.0,
    "Сүхбаатар":  1.15,
    "Чингэлтэй":  1.05,
    "Хан-Уул":    1.1,
    "Баянгол":    1.0,
    "Налайх":     0.85,
    "Багануур":   0.8,
    "Багахангай": 0.75,
}


class PriceAnalyzer:
    def __init__(self, db_pool, redis_client: aioredis.Redis):
        self.db = db_pool
        self.redis = redis_client

    async def get_market_data(self, district: str, property_type: str = "apartment") -> dict:
        """
        Тухайн дүүргийн зах зээлийн үнийн мэдээлэл.
        Redis-д cache хийнэ.
        """
        cache_key = f"price:market:{district}:{property_type}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        try:
            async with self.db.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT
                        AVG(price_per_sqm) AS avg_price,
                        MIN(price_per_sqm) AS min_price,
                        MAX(price_per_sqm) AS max_price,
                        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price_per_sqm) AS p25,
                        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price_per_sqm) AS p75,
                        COUNT(*) AS sample_count,
                        MAX(scraped_at) AS last_updated
                    FROM market_prices
                    WHERE district = $1
                      AND property_type = $2
                      AND scraped_at > NOW() - INTERVAL '30 days'
                    """,
                    district,
                    property_type,
                )
                if not row or not row["sample_count"]:
                    return self._fallback_market_data(district)

                result = {
                    "district": district,
                    "avg_price_per_sqm": int(row["avg_price"] or 0),
                    "min_price": int(row["min_price"] or 0),
                    "max_price": int(row["max_price"] or 0),
                    "p25": int(row["p25"] or 0),
                    "p75": int(row["p75"] or 0),
                    "sample_count": row["sample_count"],
                    "last_updated": str(row["last_updated"]),
                    "source": "unegui.mn + кадастрын газар",
                }

            await self.redis.setex(
                cache_key, settings.PRICE_DATA_CACHE_TTL, json.dumps(result)
            )
            return result

        except Exception as e:
            logger.error(f"Зах зээлийн дата авахад алдаа: {e}")
            return self._fallback_market_data(district)

    async def analyze_price(
        self,
        price: float,
        area_sqm: float,
        district: str,
        floor: Optional[int] = None,
        build_year: Optional[int] = None,
        property_type: str = "apartment",
    ) -> dict:
        """
        Байрны үнийг зах зээлтэй харьцуулан дүгнэлт гаргана.
        """
        market = await self.get_market_data(district, property_type)
        price_per_sqm = price / area_sqm if area_sqm else 0
        avg = market.get("avg_price_per_sqm", 1)

        # Хүрэн коэффициент тооцох
        adjusted_avg = avg * DISTRICT_PREMIUM.get(district, 1.0)

        # Давхар болон он барилт нэмэлт тооцоо
        if floor == 1 or floor and floor >= 9:
            adjusted_avg *= 0.92  # 1-р давхар, дээд давхар — хямдрал
        if build_year and build_year < 1990:
            adjusted_avg *= 0.88  # Хуучин барилга

        diff_pct = ((price_per_sqm - adjusted_avg) / adjusted_avg * 100) if adjusted_avg else 0

        # Үнэлгээ
        if diff_pct > 30:
            verdict = "overpriced"
            verdict_mn = "Зах зээлийн дунджаас мэдэгдэхүйц өндөр"
            color = "red"
        elif diff_pct > 15:
            verdict = "slightly_high"
            verdict_mn = "Зах зээлийн дунджаас арай өндөр"
            color = "orange"
        elif diff_pct < -15:
            verdict = "below_market"
            verdict_mn = "Зах зээлийн дунджаас бага — шалтгааныг шалгаарай"
            color = "blue"
        else:
            verdict = "fair"
            verdict_mn = "Зах зээлийн үнэтэй нийцэж байна"
            color = "green"

        return {
            "price_per_sqm": int(price_per_sqm),
            "market_avg_per_sqm": int(adjusted_avg),
            "diff_percent": round(diff_pct, 1),
            "verdict": verdict,
            "verdict_mn": verdict_mn,
            "color": color,
            "market_data": market,
        }

    def _fallback_market_data(self, district: str) -> dict:
        """
        DB дата байхгүй үед хэрэглэх тооцоолсон дундаж.
        2024 оны орчмын зах зээлийн мэдээлэлд суурилсан.
        """
        base_prices = {
            "Сүхбаатар":  4_500_000,
            "Баянзүрх":   3_800_000,
            "Хан-Уул":    4_200_000,
            "Чингэлтэй":  3_900_000,
            "Баянгол":    3_700_000,
        }
        base = base_prices.get(district, 3_600_000)
        return {
            "district": district,
            "avg_price_per_sqm": base,
            "min_price": int(base * 0.7),
            "max_price": int(base * 1.5),
            "sample_count": 0,
            "last_updated": None,
            "source": "тооцоолсон дундаж (дата хуучирсан байж болно)",
            "warning": "Энэ дата тооцоолсон бөгөөд зах зээлийн бодит байдлаас зөрж болно.",
        }
