"""
Татсан Excel/CSV файлуудыг боловсруулж PostgreSQL-д оруулах.

Дараах файл форматуудыг дэмждэг:
  - mcis.gov.mn-ийн тусгай зөвшөөрлийн Excel жагсаалт
  - opendata.gov.mn-ийн CSV/Excel датасет
  - Хүчингүй болгосон ТЗ-ийн жагсаалт

Хэрэглэх:
    python 04_load_to_db.py --dir output/ --type blacklist
    python 04_load_to_db.py --dir output/ --type permits
"""

import asyncio
import asyncpg
import logging
import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

DB_URL = "postgresql://user:password@localhost:5432/realestate"


def read_excel(path: Path) -> list[dict]:
    """Excel файл уншина."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
        header = [str(c).strip() if c else f"col_{i}" for i, c in enumerate(rows[0])]
        return [
            {header[i]: row[i] for i in range(min(len(header), len(row)))}
            for row in rows[1:]
            if any(row)
        ]
    except Exception as e:
        logger.error(f"Excel унших алдаа {path}: {e}")
        return []


def read_csv(path: Path) -> list[dict]:
    """CSV файл уншина."""
    import csv
    rows = []
    for enc in ("utf-8-sig", "utf-8", "cp1251", "cp866"):
        try:
            with open(path, newline="", encoding=enc) as f:
                reader = csv.DictReader(f)
                rows = [dict(r) for r in reader]
            break
        except (UnicodeDecodeError, Exception):
            continue
    return rows


def read_json(path: Path) -> list[dict]:
    """JSON файл уншина."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("data", "result", "records", "items"):
                if isinstance(data.get(key), list):
                    return data[key]
    except Exception as e:
        logger.error(f"JSON унших алдаа {path}: {e}")
    return []


def auto_read(path: Path) -> list[dict]:
    """Форматаар автоматаар уншина."""
    ext = path.suffix.lower()
    if ext in (".xlsx", ".xls"):
        return read_excel(path)
    elif ext == ".csv":
        return read_csv(path)
    elif ext == ".json":
        return read_json(path)
    return []


# ==========================================
# Хар жагсаалтын баганын нэрийг таних
# ==========================================
COMPANY_NAME_COLS = [
    "компанийн нэр", "байгууллагын нэр", "аанб нэр", "нэр",
    "company_name", "name", "организаци", "аж ахуйн нэгж",
]
REASON_COLS = [
    "шалтгаан", "тайлбар", "reason", "хүчингүй болгосон шалтгаан",
]
DATE_COLS = [
    "огноо", "хүчингүй болгосон огноо", "date", "болгосон огноо",
]
REGISTER_COLS = [
    "регистрийн дугаар", "рд", "register", "улсын регистр",
]


def detect_column(record: dict, candidates: list[str]) -> Optional[str]:
    """Баганын нэрийг жагсаалтаас олно — хэсэгчилсэн тохирол."""
    keys_lower = {k.lower().strip(): k for k in record.keys()}
    for candidate in candidates:
        cand_lower = candidate.lower()
        for key_lower, key_orig in keys_lower.items():
            if cand_lower in key_lower or key_lower in cand_lower:
                return key_orig
    return None


def normalize_company_name(name: str) -> str:
    """Компанийн нэрийг стандартчилна."""
    if not name:
        return ""
    name = str(name).upper().strip()
    for suffix in [" ХХК", " ХК", " LLC", " LTD", " CO", " CORP"]:
        name = name.replace(suffix, "")
    return re.sub(r"[^\wА-ЯӨҮа-яөү]", "", name)


async def load_blacklist(db_pool: asyncpg.Pool, records: list[dict], source: str):
    """Хар жагсаалтын компаниудыг DB-д оруулна."""
    if not records:
        return

    # Баганын нэр auto-detect
    sample = records[0]
    name_col = detect_column(sample, COMPANY_NAME_COLS)
    reason_col = detect_column(sample, REASON_COLS)
    date_col = detect_column(sample, DATE_COLS)
    register_col = detect_column(sample, REGISTER_COLS)

    logger.info(f"Баганын харуулалт:")
    logger.info(f"  Нэр: {name_col}, Шалтгаан: {reason_col}, Огноо: {date_col}")

    inserted = 0
    skipped = 0

    async with db_pool.acquire() as conn:
        for rec in records:
            company_name = str(rec.get(name_col, "") or "").strip()
            if not company_name:
                skipped += 1
                continue

            normalized = normalize_company_name(company_name)
            reason = str(rec.get(reason_col, "") or "") if reason_col else ""
            register = str(rec.get(register_col, "") or "") if register_col else ""

            # Огноо parse
            bl_date = None
            if date_col:
                date_raw = rec.get(date_col)
                if date_raw:
                    try:
                        if isinstance(date_raw, datetime):
                            bl_date = date_raw.date()
                        else:
                            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y", "%d/%m/%Y"):
                                try:
                                    bl_date = datetime.strptime(str(date_raw), fmt).date()
                                    break
                                except ValueError:
                                    continue
                    except Exception:
                        pass

            try:
                await conn.execute(
                    """
                    INSERT INTO blacklisted_companies
                        (company_name, normalized_name, reason, source,
                         blacklisted_date, updated_at)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    ON CONFLICT (normalized_name) DO UPDATE SET
                        reason = EXCLUDED.reason,
                        source = EXCLUDED.source,
                        updated_at = NOW()
                    """,
                    company_name, normalized, reason, source, bl_date,
                )
                inserted += 1
            except Exception as e:
                logger.debug(f"Insert алдаа ({company_name}): {e}")
                skipped += 1

    logger.info(f"  ✓ Хар жагсаалт: {inserted} оруулав, {skipped} алгасав")


async def load_permits(db_pool: asyncpg.Pool, records: list[dict], source: str):
    """Барилгын зөвшөөрлийн мэдээлэл оруулна."""
    PERMIT_COLS = ["зөвшөөрлийн дугаар", "permit_id", "дугаар", "tz дугаар"]
    STATUS_COLS = ["статус", "status", "төлөв"]
    ADDRESS_COLS = ["хаяг", "байршил", "address"]

    if not records:
        return

    sample = records[0]
    permit_col = detect_column(sample, PERMIT_COLS)
    name_col = detect_column(sample, COMPANY_NAME_COLS)
    status_col = detect_column(sample, STATUS_COLS)
    address_col = detect_column(sample, ADDRESS_COLS)

    inserted = 0
    async with db_pool.acquire() as conn:
        for rec in records:
            permit_id = str(rec.get(permit_col, "") or "").strip() if permit_col else ""
            company = str(rec.get(name_col, "") or "").strip() if name_col else ""
            status = str(rec.get(status_col, "") or "authorized").lower() if status_col else "authorized"
            address = str(rec.get(address_col, "") or "").strip() if address_col else ""

            if not permit_id and not company:
                continue

            # "хүчингүй" гэдэг статус → unauthorized
            if "хүчингүй" in status or "invalid" in status or "хэтэрсэн" in status:
                status = "unauthorized"

            permit_id = permit_id or f"AUTO-{normalize_company_name(company)}"

            try:
                await conn.execute(
                    """
                    INSERT INTO building_permits
                        (permit_id, company_name, address, status, updated_at)
                    VALUES ($1, $2, $3, $4, NOW())
                    ON CONFLICT (permit_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        updated_at = NOW()
                    """,
                    permit_id, company, address, status,
                )
                inserted += 1
            except Exception as e:
                logger.debug(f"Permit insert алдаа: {e}")

    logger.info(f"  ✓ Барилгын зөвшөөрөл: {inserted} оруулав")


async def process_directory(directory: Path, data_type: str):
    """
    Хавтас доторх бүх Excel/CSV/JSON файлыг боловсруулна.
    """
    db_pool = await asyncpg.create_pool(DB_URL)

    files = list(directory.rglob("*.xlsx")) + \
            list(directory.rglob("*.xls")) + \
            list(directory.rglob("*.csv")) + \
            list(directory.rglob("*.json"))

    logger.info(f"{len(files)} файл олдлоо")

    for path in files:
        if path.name.startswith(".") or "summary" in path.name:
            continue

        logger.info(f"\nБоловсруулж байна: {path.name}")
        records = auto_read(path)

        if not records:
            logger.warning(f"  Хоосон файл: {path.name}")
            continue

        logger.info(f"  {len(records)} бичлэг")
        source = f"{path.parent.name}/{path.name}"

        if data_type == "blacklist":
            await load_blacklist(db_pool, records, source)
        elif data_type == "permits":
            await load_permits(db_pool, records, source)
        else:
            # Автоматаар тодорхойлох
            sample = records[0]
            if detect_column(sample, COMPANY_NAME_COLS) and detect_column(sample, REASON_COLS):
                logger.info("  → Хар жагсаалт гэж тодорхойлов")
                await load_blacklist(db_pool, records, source)
            elif detect_column(sample, ["зөвшөөрлийн дугаар", "permit_id"]):
                logger.info("  → Зөвшөөрлийн жагсаалт гэж тодорхойлов")
                await load_permits(db_pool, records, source)

    await db_pool.close()
    logger.info("\n✅ Бүх файл боловсруулагдлаа")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Татсан файлуудыг DB-д оруулна")
    parser.add_argument("--dir", default="output", help="Файлуудын хавтас")
    parser.add_argument(
        "--type",
        choices=["blacklist", "permits", "auto"],
        default="auto",
        help="Дата төрөл",
    )
    args = parser.parse_args()

    asyncio.run(process_directory(Path(args.dir), args.type))
