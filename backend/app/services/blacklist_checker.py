"""
Хар жагсаалт болон Тусгай зөвшөөрлийн шалгалт.
Олон нийтийн бааз болон data-pipeline-с татсан CSV/JSON файлуудаас
компанийн мэдээлэл, зөвшөөрлийн хүчинтэй хугацааг шалгана.
"""

import json
import logging
import re
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import pandas as pd
import redis.asyncio as aioredis
from app.config import settings
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# Cache for CSV data in memory
_LICENSES_CACHE = []

class BlacklistChecker:
    def __init__(self, db_pool, redis_client: aioredis.Redis):
        self.db = db_pool
        self.redis = redis_client
        self.cache_ttl = settings.BLACKLIST_CACHE_TTL
        self._load_licenses_data()

    def _load_licenses_data(self):
        """
        Бүх CSV файлуудыг санах ойд нэгтгэн ачаална.
        data-pipeline/output/parsed_licenses доторх файлуудыг уншина.
        """
        global _LICENSES_CACHE
        if _LICENSES_CACHE:
            return  # Уже ачаалсан бол алгасах

        # Docker container дотор /data-pipeline-output гэж mount хийгдсэн
        # (docker-compose.yml: ../data-pipeline/output:/data-pipeline-output)
        # Host дээр ажиллуулах үед fallback зам ашиглана.
        docker_path = Path("/data-pipeline-output")
        if docker_path.exists():
            base_output = docker_path
        else:
            # Local dev fallback
            base_output = Path(__file__).resolve().parent.parent.parent.parent / "data-pipeline" / "output"

        licenses_dir = base_output / "parsed_licenses"
        blacklist_json = base_output / "blacklist_companies.json"

        logger.info(f"[BlacklistChecker] Licenses dir: {licenses_dir} (exists={licenses_dir.exists()})")
        logger.info(f"[BlacklistChecker] Blacklist JSON: {blacklist_json} (exists={blacklist_json.exists()})")

        all_records = []

        # ── 1. CSV файлуудаас тусгай зөвшөөрлийн мэдээлэл ──────────────────────
        if licenses_dir.exists():
            for csv_file in licenses_dir.glob("*.csv"):
                try:
                    df = pd.read_csv(csv_file, encoding="utf-8-sig")
                    cols = df.columns.tolist()
                    logger.info(f"[BlacklistChecker] {csv_file.name} — баганууд: {cols}")

                    # MCUD-ийн CSV баганын нэрстэй тохируулах
                    name_col = next(
                        (c for c in cols if any(k in c for k in ['ААНБ-ын нэр', 'ААН', 'ТЗААН', 'Байгууллагын нэр'])),
                        None
                    )
                    date_col = next(
                        (c for c in cols if any(k in c.lower() for k in ['дуусах огноо', 'хүчинтэй', 'дуусах'])),
                        None
                    )

                    if not name_col:
                        logger.warning(f"[BlacklistChecker] {csv_file.name}: нэрийн багана олдсонгүй — алгасав")
                        continue

                    loaded = 0
                    for _, row in df.iterrows():
                        company_name = str(row[name_col]).strip()
                        # Skip empty, NaN, numeric-only, or header-like junk rows
                        if not company_name or company_name in ('nan', '') or company_name.isdigit():
                            continue
                        # Skip values that are clearly not company names (single chars, №, numbers)
                        if len(company_name) < 3 or company_name in ('№', 'N', 'n'):
                            continue

                        expiry_date_str = str(row[date_col]).strip() if date_col else "Тодорхойгүй"
                        is_expired = False

                        if expiry_date_str and expiry_date_str not in ('nan', 'Тодорхойгүй', ''):
                            for fmt in ("%Y.%m.%d", "%m/%d/%Y", "%Y-%m-%d", "%d.%m.%Y"):
                                try:
                                    expiry_date = datetime.strptime(expiry_date_str.split(' ')[0], fmt)
                                    is_expired = expiry_date < datetime.now()
                                    expiry_date_str = expiry_date.strftime("%Y-%m-%d")
                                    break
                                except ValueError:
                                    pass

                        all_records.append({
                            "source_file": csv_file.name,
                            "company_name": company_name,
                            "normalized_name": self._normalize_name(company_name),
                            "expiry_date": expiry_date_str,
                            "is_expired": is_expired,
                            "is_blacklisted": False,
                            "raw_data": {}
                        })
                        loaded += 1

                    logger.info(f"[BlacklistChecker] {csv_file.name}: {loaded} компани ачааллаа")

                except Exception as e:
                    logger.error(f"Файл уншихад алдаа {csv_file.name}: {e}")
        else:
            logger.warning(f"[BlacklistChecker] Зөвшөөрлийн хавтас олдсонгүй: {licenses_dir}")

        # ── 2. blacklist_companies.json (02_mcis_license_scraper-аас үүссэн) ────
        if blacklist_json.exists():
            try:
                with open(blacklist_json, encoding="utf-8") as f:
                    bl_records = json.load(f)
                for rec in bl_records:
                    company_name = str(rec.get("company_name", "")).strip()
                    if not company_name:
                        continue
                    expiry_date_str = str(rec.get("expiry_date", "Тодорхойгүй"))
                    is_expired = rec.get("is_expired", False)
                    all_records.append({
                        "source_file": "blacklist_companies.json",
                        "company_name": company_name,
                        "normalized_name": self._normalize_name(company_name),
                        "expiry_date": expiry_date_str,
                        "is_expired": is_expired,
                        "is_blacklisted": True,
                        "raw_data": rec
                    })
                logger.info(f"[BlacklistChecker] blacklist_companies.json: {len(bl_records)} компани ачааллаа")
            except Exception as e:
                logger.error(f"blacklist_companies.json уншихад алдаа: {e}")

        _LICENSES_CACHE = all_records
        logger.info(f"[BlacklistChecker] Санах ойд НИЙТ {len(_LICENSES_CACHE)} мэдээлэл ачааллаа.")


    def _fuzzy_match(self, query: str, target: str) -> float:
        return SequenceMatcher(None, query, target).ratio()

    async def check(self, company_name: str) -> dict:
        """
        Компанийн нэрийг хар жагсаалт болон тусгай зөвшөөрлийн мэдээлэлтэй тулгана.
        Хэсэгчилсэн тохирол (fuzzy match) хийнэ.
        """
        normalized_query = self._normalize_name(company_name)
        if len(normalized_query) < 2:
            return {"found": False, "error": "Хайлтын утга хэт богино байна."}

        cache_key = f"company_check:{normalized_query}"

        # Cache шалгах
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        result = {
            "query": company_name,
            "blacklisted": False,
            "license_status": "Тодорхойгүй",
            "matches": []
        }

        # 1. DB хар жагсаалт шалгах
        try:
            blacklist_result = await self._query_blacklist(normalized_query)
            if blacklist_result.get("found"):
                result["blacklisted"] = True
                result["blacklist_info"] = blacklist_result
        except Exception as e:
            logger.error(f"DB хар жагсаалт шалгахад алдаа: {e}")

        # 2. Тусгай зөвшөөрлийн файлуудаас хайх
        matches = []
        for record in _LICENSES_CACHE:
            # Бүрэн эсвэл хэсэгчлэн тохирох
            target_norm = record["normalized_name"]
            
            # Substring match
            if normalized_query in target_norm or target_norm in normalized_query:
                matches.append({"record": record, "score": 1.0})
                continue
                
            # Fuzzy match
            score = self._fuzzy_match(normalized_query, target_norm)
            if score > 0.75:  # Төстэй байдлын босго 75%
                matches.append({"record": record, "score": score})

        # Хамгийн их тохирсон үр дүнгүүдийг эрэмбэлэх
        matches.sort(key=lambda x: x["score"], reverse=True)
        top_matches = matches[:5] # Топ 5 илэрц
        
        if top_matches:
            result["found"] = True
            
            # Format output matches
            formatted_matches = []
            for m in top_matches:
                rec = m["record"]
                is_bl = rec.get("is_blacklisted", False)
                if is_bl:
                    result["blacklisted"] = True
                formatted_matches.append({
                    "company_name": rec["company_name"],
                    "is_expired": rec["is_expired"],
                    "expiry_date": rec["expiry_date"],
                    "source": rec["source_file"],
                    "is_blacklisted": is_bl,
                    "match_score": f"{m['score']*100:.0f}%"
                })
            
            result["matches"] = formatted_matches
            
            # Ерөнхий төлөв тодорхойлох
            best_match = top_matches[0]["record"]
            if best_match["is_expired"]:
                result["license_status"] = "Тусгай зөвшөөрлийн хугацаа ДУУССАН"
            else:
                result["license_status"] = "Тусгай зөвшөөрөл ХҮЧИНТЭЙ"
        else:
            result["found"] = False
            result["message"] = "Уг компани хар жагсаалтад болон тусгай зөвшөөрлийн санд олдсонгүй."

        # Cache-д хадгалах
        await self.redis.setex(cache_key, self.cache_ttl, json.dumps(result))
        return result

    async def suggest(self, query: str, limit: int = 8) -> list[str]:
        """
        Хэрэглэгч бичиж байх үед autocomplete санал гаргана.
        Substring + fuzzy match ашиглан хамгийн их тохирсон компанийн нэрсийг буцаана.
        """
        self._load_licenses_data()
        normalized_query = self._normalize_name(query)
        if len(normalized_query) < 2:
            return []

        seen: set[str] = set()
        results: list[dict] = []

        for record in _LICENSES_CACHE:
            name = record["company_name"]
            norm = record["normalized_name"]

            # Давхардал алгасах
            if name in seen:
                continue

            # Substring тохирол (хурдан, хамгийн өндөр приоритет)
            if normalized_query in norm:
                results.append({"name": name, "score": 1.0 + len(normalized_query) / max(len(norm), 1)})
                seen.add(name)
                continue

            # Fuzzy match (удаан, зөвхөн богино query-д)
            if len(normalized_query) >= 3:
                score = self._fuzzy_match(normalized_query, norm)
                if score > 0.6:
                    results.append({"name": name, "score": score})
                    seen.add(name)

        results.sort(key=lambda x: x["score"], reverse=True)
        return [r["name"] for r in results[:limit]]

    async def check_permit_blacklist(self, permit_id: str) -> dict:
        """Барилгын зөвшөөрлийн дугаараар хар жагсаалт шалгана."""
        cache_key = f"blacklist:permit:{permit_id}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        try:
            async with self.db.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT
                        bl.*,
                        bp.company_name,
                        bp.permit_status
                    FROM building_permits bp
                    LEFT JOIN blacklisted_buildings bl ON bl.permit_id = bp.permit_id
                    WHERE bp.permit_id = $1
                    """,
                    permit_id,
                )
                if not row:
                    result = {"found": False}
                elif row["permit_status"] in ("unauthorized", "illegal"):
                    result = {
                        "found": True,
                        "type": "unauthorized_building",
                        "reason": "Зөвшөөрөлгүй баригдсан барилга",
                        "company": row["company_name"],
                        "updated_at": str(row.get("updated_at", "")),
                    }
                else:
                    result = {"found": False}

            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(result))
            return result
        except Exception as e:
            logger.error(f"Зөвшөөрлийн хар жагсаалт шалгахад алдаа: {e}")
            return {"found": False, "error": str(e)}

    async def get_all_blacklisted(self, page: int = 1, limit: int = 50) -> dict:
        """Бүх хар жагсаалтын компаниудыг буцаана (хуудасчлалтай)."""
        offset = (page - 1) * limit
        try:
            async with self.db.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        company_name,
                        reason,
                        source,
                        blacklisted_date,
                        updated_at
                    FROM blacklisted_companies
                    ORDER BY blacklisted_date DESC
                    LIMIT $1 OFFSET $2
                    """,
                    limit,
                    offset,
                )
                total = await conn.fetchval("SELECT COUNT(*) FROM blacklisted_companies")
                return {
                    "items": [dict(r) for r in rows],
                    "total": total,
                    "page": page,
                    "pages": (total + limit - 1) // limit,
                }
        except Exception as e:
            logger.error(f"Хар жагсаалт авахад алдаа: {e}")
            return {"items": [], "total": 0, "page": 1, "pages": 0}

    async def _query_blacklist(self, normalized_name: str) -> dict:
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT company_name, reason, source, blacklisted_date, updated_at
                FROM blacklisted_companies
                WHERE normalized_name = $1
                """,
                normalized_name,
            )
            if row:
                return {
                    "found": True,
                    "company": row["company_name"],
                    "reason": row["reason"],
                    "source": row["source"],
                    "blacklisted_date": str(row["blacklisted_date"]),
                    "updated_at": str(row["updated_at"]),
                }

            rows = await conn.fetch(
                """
                SELECT company_name, reason, source, updated_at
                FROM blacklisted_companies
                WHERE normalized_name ILIKE $1
                LIMIT 3
                """,
                f"%{normalized_name}%",
            )
            if rows:
                return {
                    "found": True,
                    "partial_match": True,
                    "matches": [dict(r) for r in rows],
                    "warning": "Нэр хэсэгчлэн тохирч байна. Нарийвчлан шалгаарай.",
                }
            return {"found": False}

    def _normalize_name(self, name: str) -> str:
        """Компанийн нэрийг стандартчилна."""
        name = name.strip().upper()
        suffixes = [" ХХК", " ХК", " LLC", " LTD", " CO", " CORP", " INC", " ХХАА", " НӨХӨРЛӨЛ"]
        for suffix in suffixes:
            name = name.replace(suffix, "")
        name = re.sub(r'[^\w\s]', '', name)
        return name.strip()
