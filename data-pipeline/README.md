# Дата татах гарын авлага

## Хоёр эх сурвалжийн тухай бодит байдал

### opendata.gov.mn
✅ **CKAN API — шууд ашиглаж болно**
Нэвтрэх эрх шаардахгүй, стандарт REST API байдаг.

### license.mn / mcis.gov.mn  
⚠️ **React SPA — илүү хүчин чармайлт шаардана**
- `license.mn` нь JavaScript-р ажилладаг тул энгийн tatах боломжгүй
- `mcis.gov.mn` нь robots.txt-д автомат хандалтыг хориглосон
- Гэхдээ жагсаалтын Excel файлуудыг нийтэд тавьдаг

---

## Алхам 1 — Суулгах

```bash
pip install httpx playwright openpyxl beautifulsoup4 asyncpg
playwright install chromium
```

---

## Алхам 2 — opendata.gov.mn-ээс дата татах

```bash
python 01_opendata_ckan.py
```

**Юу хийдэг:**
- CKAN API-г ашиглан барилгын холбоотой бүх dataset хайна
- CSV / Excel файлуудыг `output/opendata/` хавтасд татна
- `summary.json`-д бүх файлын жагсаалт хадгална

**Хамааралтай dataset-үүд:**
- `Барилга угсралтын тусгай зөвшөөрөлтэй ААНБ`
- `Зураг төслийн тусгай зөвшөөрөлтэй ААНБ`  
- `Хүчингүй болгосон тусгай зөвшөөрөл`

---

## Алхам 3 — license.mn / mcis.gov.mn-ийн дата

### 3a. Эхлээд API endpoint хайх оролдлого

```bash
python 02_mcis_license_scraper.py
```

Хэрэв `found_apis.json` файл үүссэн бол → API олдсон, шууд ашиглаж болно.

### 3b. Playwright ашиглах (JavaScript render)

```bash
# license.mn
python 03_playwright_license_mn.py

# mcis.gov.mn grants хуудас
python 03_playwright_license_mn.py mcis
```

**Playwright юу хийдэг:**
- Бодит Chromium хөтөч ажиллуулна
- Хуудасны бүх API дуудалтыг бүртгэнэ
- Хүснэгтийн мэдээллийг авна
- `output/license_mn/license_mn_data.json`-д хадгална

### 3c. Chrome DevTools-р API олох (хамгийн найдвартай)

1. Chrome-д `https://license.mn` нээнэ
2. `F12` → **Network** tab → **Fetch/XHR** шүүнэ
3. Хуудасны аль нэг хэсэгт хандахад (жишээ: тусгай зөвшөөрлийн жагсаалт)
   Network tab-д API дуудалтууд гарна
4. `api/`, `v1/`, `licenses` гэсэн URL-уудыг хайна
5. Олсон URL-г `02_mcis_license_scraper.py`-ийн `candidate_endpoints` жагсаалтад нэмнэ

### 3d. Шууд Excel татах

mcis.gov.mn тусгай зөвшөөрлийн жагсаалтыг Excel-ээр нийтэлдэг:

```
https://mcis.gov.mn/mn/grants
```

Энэ хуудсан дахь Excel холбоосуудыг гараар татаж `output/mcis/` хавтасд хийнэ.

---

## Алхам 4 — Дата DB-д оруулах

```bash
# Хар жагсаалт
python 04_load_to_db.py --dir output/ --type blacklist

# Барилгын зөвшөөрөл
python 04_load_to_db.py --dir output/ --type permits

# Автомат тодорхойлох
python 04_load_to_db.py --dir output/ --type auto
```

---

## Практик зөвлөмж

| Нөхцөл | Шийдэл |
|--------|--------|
| opendata.gov.mn CSV байна | `01_opendata_ckan.py` — хамгийн хурдан |
| license.mn JSON API олдсон | `02_mcis_license_scraper.py`-д нэмэх |
| license.mn API олдсонгүй | `03_playwright_license_mn.py` |
| Excel файл гараар татсан | `04_load_to_db.py` |
| Байгууллагад хандах | МБҮА: 70111515 |

---

## Тэмдэглэл

- `mcis.gov.mn` robots.txt-д `Disallow: /` байна → Playwright-г
  хурдан click хийдэг байлгах, хоорондоо 1–2 секунд хүлээх
- Татсан датаг заавал `updated_at` огноотойгоор хадгалах —
  хэрэглэгчид "хэзээ шинэчлэгдсэн" харуулахад чухал
- Хар жагсаалт дата хуучирвал иргэдийг төөрөгдүүлнэ,
  тиймээс 2 долоо хоногт нэг шинэчлэх scheduler заавал байх
