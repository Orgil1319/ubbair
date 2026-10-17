"""
Автомат дата шинэчлэлтийн scheduler.
APScheduler ашиглан 2 долоо хоног тутам бүх дата эх сурвалжийг шинэчилнэ.
"""

import asyncio
import asyncpg
import logging
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

from ingestion.nkhbhg_fetcher import NKHBHGFetcher
from ingestion.price_scraper import PriceScraper
from ingestion.gis_loader import GISLoader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("scheduler")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/realestate",
)

async def refresh_all_data():
    """
    Бүх дата эх сурвалжийг шинэчилнэ.
    Алдаа гарвал тухайн эх сурвалжийг алгасаж үргэлжилнэ.
    """
    start = datetime.utcnow()
    logger.info(f"=== Дата шинэчлэлт эхэллээ: {start.isoformat()} ===")

    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    results = {}

    try:
        # 1. НХБХГ — хар жагсаалт, зөвшөөрөлгүй барилга
        logger.info("1/3 НХБХГ дата татаж байна...")
        fetcher = NKHBHGFetcher(db_pool)
        try:
            results["nkhbhg"] = await fetcher.fetch_all()
        except Exception as e:
            logger.error(f"НХБХГ алдаа: {e}")
            results["nkhbhg"] = {"error": str(e)}
        finally:
            await fetcher.close()

        # 2. Үнийн дата — unegui.mn
        logger.info("2/3 Үнийн дата татаж байна...")
        scraper = PriceScraper(db_pool)
        try:
            results["prices"] = await scraper.fetch_all_districts()
        except Exception as e:
            logger.error(f"Үнийн дата алдаа: {e}")
            results["prices"] = {"error": str(e)}
        finally:
            await scraper.close()

        # 3. GIS дата — үерийн бүс (сард 1 удаа хийхэд хангалттай)
        logger.info("3/3 GIS дата шинэчилж байна...")
        gis_loader = GISLoader(db_pool)
        try:
            results["gis"] = await gis_loader.refresh_if_needed()
        except Exception as e:
            logger.error(f"GIS дата алдаа: {e}")
            results["gis"] = {"error": str(e)}

        # Шинэчлэлтийн лог хадгалах
        await _log_refresh(db_pool, results, start)

    finally:
        await db_pool.close()

    duration = (datetime.utcnow() - start).total_seconds()
    logger.info(f"=== Дата шинэчлэлт дуусав: {duration:.1f}с ===")
    return results


async def _log_refresh(db_pool, results: dict, started_at: datetime):
    """
    Шинэчлэлтийн үр дүнг лог хүснэгтэд хадгална.
    """
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO data_refresh_log (started_at, finished_at, results)
                VALUES ($1, NOW(), $2)
                """,
                started_at,
                str(results),
            )
    except Exception as e:
        logger.error(f"Лог хадгалахад алдаа: {e}")


def main():
    scheduler = AsyncIOScheduler()

    # 2 долоо хоног тутам шинэчилнэ
    scheduler.add_job(
        refresh_all_data,
        trigger=IntervalTrigger(weeks=2),
        id="full_refresh",
        name="Бүх дата шинэчлэлт",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 цагийн дотор дахин оролдоно
    )

    # Эхний удаа тэр дор нь ажиллуулна
    scheduler.add_job(
        refresh_all_data,
        id="startup_refresh",
        name="Эхлүүлэх үеийн шинэчлэлт",
    )

    scheduler.start()
    logger.info("Scheduler эхэллээ. 2 долоо хоног тутам дата шинэчлэгдэнэ.")

    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler зогслоо.")


if __name__ == "__main__":
    main()
