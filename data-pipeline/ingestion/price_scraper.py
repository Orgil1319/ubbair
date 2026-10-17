"""
unegui.mn-ийн байрны үнийн дата татах.
Зах зээлийн бодит үнийн шинжилгээнд ашиглана.

ТЭМДЭГЛЭЛ: Web scraping хийхээс өмнө unegui.mn-ийн
үйлчилгээний нөхцөлийг уншиж, зөвшөөрөл авах шаардлагатай.
Хэрэв нийтийн API байвал тэрийгээ ашиглах нь дээр.
"""

import asyncio
import asyncpg
import httpx
import logging
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

UB_DISTRICTS = [
    "Баянзүрх", "Сүхбаатар", "Чингэлтэй",
    "Хан-Уул", "Баянгол", "Налайх",
]

# Хэрэглэгчийн agent — scraping-ийн стандарт ёс зүй
HEADERS = {
    "User-Agent": "MongolianRealEstateAdvisor/1.0 (Consumer protection research; contact@yourdomain.mn)",
}


class PriceScraper:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.client = httpx.AsyncClient(
            headers=HEADERS,
            timeout=20.0,
            follow_redirects=True,
        )

    async def fetch_all_districts(self) -> dict:
        """
        Улаанбаатарын бүх дүүргийн байрны үнийн дата татана.
        Rate limit хэтрүүлэхгүйн тулд хооронд нь 2 секунд хүлээнэ.
        """
        results = {}
        for district in UB_DISTRICTS:
            logger.info(f"Үнийн дата татаж байна: {district}")
            try:
                count = await self.fetch_district(district)
                results[district] = {"success": True, "count": count}
                await asyncio.sleep(2)  # Rate limit
            except Exception as e:
                logger.error(f"{district} дүүргийн дата алдаа: {e}")
                results[district] = {"success": False, "error": str(e)}
        return results

    async def fetch_district(self, district: str) -> int:
        """
        Тодорхой дүүргийн байрны зарын дата татана.

        АНХААРУУЛГА: Доорх URL болон CSS selector нь
        unegui.mn-ийн бодит хуудасны бүтцэд тааруулах шаардлагатай.
        Хэрэв site бүтэц өөрчлөгдвөл шинэчлэх хэрэгтэй.
        """
        # Хэрэв unegui.mn нийтийн API-тай бол тэрийгээ ашиглана
        # Жишээ endpoint (бодит API-г нь судлах хэрэгтэй):
        # url = f"https://api.unegui.mn/v1/properties?district={district}&type=apartment"

        # Хэрэв API байхгүй бол HTML parse хийнэ
        url = f"https://www.unegui.mn/l-hdlh/l-hdlh-zarna/ulaanbaatar/{self._district_to_slug(district)}/"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            listings = self._parse_listings(response.text, district)
            return await self._store_listings(listings)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP алдаа {district}: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Parse алдаа {district}: {e}")
            raise

    def _parse_listings(self, html: str, district: str) -> list[dict]:
        """
        HTML-ээс байрны мэдээлэл гаргана.
        BeautifulSoup ашигладаг — pip install beautifulsoup4 хэрэгтэй.

        Бодит хэрэгжилтэд unegui.mn-ийн HTML бүтцийг
        шалгаж selector-уудыг тааруулах шаардлагатай.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.error("beautifulsoup4 суулгаагүй байна: pip install beautifulsoup4")
            return []

        soup = BeautifulSoup(html, "html.parser")
        listings = []

        # АНХААРУУЛГА: Доорх selector-ууд тааруулах шаардлагатай
        for card in soup.select(".announcement-container"):
            try:
                price_text = card.select_one(".price-primary")
                area_text = card.select_one(".announcement-description")
                title_text = card.select_one("h3.announcement-block__title")

                if not price_text:
                    continue

                price = self._parse_price(price_text.get_text())
                area = self._parse_area(area_text.get_text() if area_text else "")

                if price and area:
                    listings.append({
                        "district": district,
                        "price": price,
                        "area_sqm": area,
                        "price_per_sqm": int(price / area),
                        "title": title_text.get_text().strip() if title_text else "",
                        "property_type": "apartment",
                        "scraped_at": datetime.utcnow().isoformat(),
                    })
            except Exception as e:
                logger.debug(f"Card parse алдаа: {e}")
                continue

        logger.info(f"{district}: {len(listings)} зар олдлоо")
        return listings

    def _parse_price(self, text: str) -> Optional[int]:
        """
        "150,000,000 ₮" → 150000000
        """
        cleaned = re.sub(r'[^\d]', '', text)
        if cleaned and len(cleaned) >= 6:
            price = int(cleaned)
            # Хэт бага эсвэл хэт их үнэ хасна
            if 5_000_000 <= price <= 5_000_000_000:
                return price
        return None

    def _parse_area(self, text: str) -> Optional[float]:
        """
        "65 м²" → 65.0
        """
        match = re.search(r'(\d+(?:\.\d+)?)\s*м', text)
        if match:
            area = float(match.group(1))
            if 10 <= area <= 500:
                return area
        return None

    def _district_to_slug(self, district: str) -> str:
        slugs = {
            "Баянзүрх": "bayanzurh",
            "Сүхбаатар": "sukhbaatar",
            "Чингэлтэй": "chingeltei",
            "Хан-Уул": "khan-uul",
            "Баянгол": "bayangol",
            "Налайх": "nalaikh",
        }
        return slugs.get(district, district.lower())

    async def _store_listings(self, listings: list[dict]) -> int:
        if not listings:
            return 0
        count = 0
        async with self.db.acquire() as conn:
            for item in listings:
                await conn.execute(
                    """
                    INSERT INTO market_prices
                        (district, price, area_sqm, price_per_sqm, property_type, scraped_at)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    """,
                    item["district"],
                    item["price"],
                    item["area_sqm"],
                    item["price_per_sqm"],
                    item["property_type"],
                )
                count += 1
        return count

    async def close(self):
        await self.client.aclose()
