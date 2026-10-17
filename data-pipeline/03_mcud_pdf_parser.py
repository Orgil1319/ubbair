"""
MCUD PDF файлуудаас Тусгай зөвшөөрлийн хүснэгтүүдийг татах скрипт
===================================================================
Энэхүү скрипт нь `data-pipeline/output/mcud_licenses` доторх PDF
файлуудаас `pdfplumber` ашиглан хүснэгт уншиж, цэвэрлэсэн өгөгдлийг
JSON болон CSV файл болгон хадгална.
"""

import os
import json
import logging
import pandas as pd
import pdfplumber
from pathlib import Path

# ── Logging тохиргоо ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Тохиргоо ─────────────────────────────────────────────────────────────────
INPUT_DIR = Path(__file__).parent / "output" / "mcud_licenses"
OUTPUT_DIR = Path(__file__).parent / "output" / "parsed_licenses"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Боловсруулах PDF файлууд (Таны саяхан татсан файлууд)
PDF_FILES = [
    "a1725_БАРИЛГА БАЙГУУЛАМЖ 2026.01.30-НЫ ӨДРИЙН БАЙДЛААР OPENDATA 1 1.pdf",
    "a1726_ЗУРАГ ТӨСӨЛ 2026.01.30-НЫ ӨДРИЙН БАЙДЛААР OPENDATA 1.pdf",
    "a1746_Хот байгуулалтын баримт бичиг боловсруулах эрхтэй ААН 2026.06.pdf"
]

def clean_text(text):
    """Шинэ мөр болон илүүдэл зайг цэвэрлэх"""
    if pd.isna(text) or text is None:
        return ""
    return str(text).replace("\n", " ").strip()

def parse_pdf_to_dataframe(pdf_path: Path) -> pd.DataFrame:
    """PDF файлаас хүснэгтийг уншиж DataFrame болгох"""
    log.info(f"Уншиж байна: {pdf_path.name}")
    all_rows = []
    headers = None

    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            log.info(f"  Нийт хуудас: {total_pages}")
            
            for i, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if not tables:
                    continue
                
                # Хуудас бүрийн эхний хүснэгтийг авна (Ихэвчлэн ганц л том хүснэгт байгаа)
                table = tables[0]
                
                # Эхний хуудаснаас header-ийг авна
                if i == 0 and len(table) > 0:
                    headers = [clean_text(h) for h in table[0]]
                    all_rows.extend(table[1:])
                else:
                    # Хэрэв эхний мөр нь header шиг харагдаж байвал (№, Регистр г.м) алгасна
                    if table and table[0] and "№" in str(table[0][0]):
                        all_rows.extend(table[1:])
                    else:
                        all_rows.extend(table)
                        
                if i % 10 == 0 and i > 0:
                    log.info(f"  ... боловсруулсан: {i}/{total_pages} хуудас")

    except Exception as e:
        log.error(f"Алдаа гарлаа {pdf_path.name}: {e}")
        return pd.DataFrame()

    if not all_rows:
        return pd.DataFrame()

    # Хэрэв header олдсон бол DataFrame үүсгэх
    df = pd.DataFrame(all_rows, columns=headers if headers and len(headers) == len(all_rows[0]) else None)
    
    # Бүх нүдний датаг цэвэрлэх
    df = df.map(clean_text)
    
    # Хоосон эсвэл зөвхөн дугаартай мөрүүдийг устгах
    df = df.dropna(how='all')
    
    log.info(f"  → Нийт {len(df)} мөр өгөгдөл олдлоо.")
    return df

def main():
    log.info("=" * 60)
    log.info("PDF Parser скрипт ажиллаж эхэллээ")
    log.info("=" * 60)

    for filename in PDF_FILES:
        pdf_path = INPUT_DIR / filename
        if not pdf_path.exists():
            log.warning(f"Файл олдсонгүй (Алгасаж байна): {filename}")
            continue

        df = parse_pdf_to_dataframe(pdf_path)
        if df.empty:
            continue

        # Гаралтын файлын нэр (PDF-ийн нэрнээс .pdf-г хасна)
        base_name = pdf_path.stem
        csv_path = OUTPUT_DIR / f"{base_name}.csv"
        json_path = OUTPUT_DIR / f"{base_name}.json"

        # CSV хэлбэрээр хадгалах
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        # JSON хэлбэрээр хадгалах
        json_data = df.to_dict(orient="records")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        log.info(f"Хадгаллаа: {csv_path.name}")
        log.info(f"Хадгаллаа: {json_path.name}\n")

    log.info("=" * 60)
    log.info("БҮХ АЖИЛ ДУУСЛАА!")
    log.info(f"Гаралтын хавтас: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
