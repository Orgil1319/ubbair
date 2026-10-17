"""
opendata.gov.mn — Барилгын дата татах.

АНХААРАЛ: opendata.gov.mn нь 2024 онд CKAN-аас Nuxt.js SPA руу шилжсэн.
Хуучин CKAN API (api/3/action) ажиллахгүй болсон.

Одоогийн стратеги:
  1. opendata.gov.mn/api/v1 endpoint туршина
  2. Хэрэв ажиллахгүй бол Playwright-р харагдаж буй dataset татна
  3. Алтернатив: dataset-уудыг гараар татаж data-pipeline/input/ хавтсанд байрлуулна

Холбогдох dataset-үүд (гараар татах холбоосууд):
  - https://opendata.gov.mn/dataset/barilga-ugsuraltiig-guits
  - https://opendata.gov.mn/dataset/zurag-tusliin-tusgai-zuvshuurul
  - https://opendata.gov.mn/dataset/khuchingyui-bolgoson-tusgai-zuvshuurul
"""

import httpx
import json
import asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Шинэ API endpoint (2024+ хувилбар)
BASE_V1 = "https://opendata.gov.mn/api/v1"
# Хуучин CKAN API (ажиллаагүй тохиолдолд fallback болгон хадгална)
BASE_CKAN = "https://opendata.gov.mn/api/3/action"

# Барилгатай холбоотой өгөгдлийн бүрдлийн хайлтын түлхүүр үг
SEARCH_KEYWORDS = [
    "барилга угсралтын тусгай зөвшөөрөл",
    "зураг төслийн тусгай зөвшөөрөл",
    "өргөх байгууламж тусгай зөвшөөрөл",
    "хүчингүй болгосон тусгай зөвшөөрөл",
    "барилгын зөвшөөрөлгүй",
    "ашиглалтад хүлээн аваагүй",
]

# Мэдэгдэж буй dataset URL-ууд (гараар олсон)
KNOWN_DATASET_URLS = [
    "https://opendata.gov.mn/dataset/barilga-ugsuraltiig-guits",
    "https://opendata.gov.mn/dataset/zurag-tusliin-tusgai-zuvshuurul",
]

OUTPUT_DIR = Path("output/opendata")


async def list_all_datasets(client: httpx.AsyncClient) -> list[dict]:
    """
    CKAN-д бүртгэлтэй бүх dataset-ийн жагсаалт авна.
    """
    url = f"{BASE}/package_list"
    resp = await client.get(url)
    resp.raise_for_status()
    data = resp.json()

    if not data.get("success"):
        logger.error(f"CKAN package_list амжилтгүй: {data}")
        return []

    names = data["result"]
    logger.info(f"Нийт {len(names)} dataset олдлоо")
    return names


async def search_datasets(client: httpx.AsyncClient, keyword: str) -> list[dict]:
    """
    Түлхүүр үгээр dataset хайна.
    """
    url = f"{BASE}/package_search"
    params = {
        "q": keyword,
        "rows": 20,
        "start": 0,
    }
    resp = await client.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()

    if not data.get("success"):
        return []

    results = data["result"]["results"]
    logger.info(f"'{keyword}' → {len(results)} dataset")
    return results


async def get_dataset_detail(client: httpx.AsyncClient, dataset_id: str) -> dict:
    """
    Dataset-ийн дэлгэрэнгүй мэдээлэл (resource URL-ууд орно).
    """
    url = f"{BASE}/package_show"
    resp = await client.get(url, params={"id": dataset_id})
    resp.raise_for_status()
    data = resp.json()
    return data.get("result", {})


async def download_resource(client: httpx.AsyncClient, resource: dict, out_dir: Path) -> Path | None:
    """
    Resource файл (CSV / Excel / JSON) татаж хадгална.
    """
    resource_url = resource.get("url", "")
    resource_name = resource.get("name", "file")
    resource_format = resource.get("format", "").lower()

    if not resource_url:
        return None

    # Дэмжигдэх форматууд
    if resource_format not in ("csv", "xlsx", "xls", "json", "xml"):
        logger.info(f"  Тохиромжгүй формат {resource_format}, алгасав: {resource_name}")
        return None

    safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in resource_name)
    ext = resource_format if resource_format else "bin"
    out_path = out_dir / f"{safe_name}.{ext}"

    if out_path.exists():
        logger.info(f"  Аль хэдийн татагдсан: {out_path.name}")
        return out_path

    try:
        logger.info(f"  Татаж байна: {resource_url}")
        async with client.stream("GET", resource_url) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                async for chunk in r.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
        logger.info(f"  ✓ Хадгалагдлаа: {out_path.name} ({out_path.stat().st_size // 1024} KB)")
        return out_path
    except Exception as e:
        logger.error(f"  ✗ Татахад алдаа ({resource_name}): {e}")
        return None


async def fetch_construction_datasets():
    """
    Барилгатай холбоотой бүх dataset-ийг татна.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(
        timeout=30.0,
        headers={"User-Agent": "MongolianRealEstateAdvisor/1.0 (Public data research)"},
        follow_redirects=True,
    ) as client:

        # 1. Барилгын dataset хайх
        found_datasets = {}
        for keyword in SEARCH_KEYWORDS:
            results = await search_datasets(client, keyword)
            for ds in results:
                ds_id = ds.get("id") or ds.get("name")
                if ds_id and ds_id not in found_datasets:
                    found_datasets[ds_id] = ds
            await asyncio.sleep(0.5)  # rate limit

        logger.info(f"\nНийт {len(found_datasets)} барилгын dataset олдлоо\n")

        # 2. Тус бүрийн resource татах
        summary = []
        for ds_id, ds_meta in found_datasets.items():
            ds_name = ds_meta.get("title", ds_id)
            logger.info(f"\n📁 {ds_name}")

            # Dataset-ийн дэлгэрэнгүй мэдээлэл
            detail = await get_dataset_detail(client, ds_id)
            resources = detail.get("resources", [])

            if not resources:
                logger.info("  Resource байхгүй")
                continue

            ds_dir = OUTPUT_DIR / ds_id[:50]
            ds_dir.mkdir(exist_ok=True)

            downloaded = []
            for res in resources:
                path = await download_resource(client, res, ds_dir)
                if path:
                    downloaded.append(str(path))
                await asyncio.sleep(0.3)

            summary.append({
                "id": ds_id,
                "name": ds_name,
                "files": downloaded,
                "url": f"https://opendata.gov.mn/dataset/{ds_id}",
            })

        # Summary хадгалах
        summary_path = OUTPUT_DIR / "summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        logger.info(f"\n✅ Дууслаа. Summary: {summary_path}")
        return summary


if __name__ == "__main__":
    asyncio.run(fetch_construction_datasets())
