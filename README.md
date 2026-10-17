# 🏠 Монголын Үл Хөдлөх Хөрөнгийн AI Зөвлөх

Иргэдийг байрны луйвар, чанаргүй барилга, үерийн бүс, хөрсний
нуралтаас хамгаалах AI-д суурилсан зөвлөх систем.

## Гол функцүүд

- 🔴 **Эрсдэлийн үнэлгээ** — үер, хөрс, газар хөдлөлт, барилгын зөвшөөрөл
- ⚠️ **Хар жагсаалт** — НХБХГ, МХГ-ын жагсаалтаар компани шалгах
- 💰 **Үнийн шинжилгээ** — зах зээлтэй харьцуулж хөөс тодорхойлох
- 📄 **Гэрээ үүсгэх** — Иргэний хуулийн 318-р зүйлд нийцсэн PDF гэрээ
- 🤖 **AI зөвлөгч** — Claude-тай монгол хэлээр чатлах
- 📚 **Хуулийн мэдлэг** — RAG-аар Иргэний хуулийн заалтад тулгуурлан хариулна

## Технологийн стек

| Давхарга | Технологи |
|----------|-----------|
| Frontend | Next.js 15, TypeScript, Leaflet |
| Backend  | Python 3.12, FastAPI, asyncpg |
| Database | PostgreSQL 16 + PostGIS + pgvector, Redis |
| AI       | Groq (Llama) эсвэл OpenAI + RAG |
| Deploy   | Vercel (frontend), Railway (backend+db) |

## Хурдан эхлэх

### A. GitHub Codespaces (суулгах зүйлгүй)

1. GitHub дээр **Code → Codespaces → Create codespace on main** дарна.
2. Анх асахад `.env` автоматаар үүсч, бүх сервис (PostgreSQL, Redis, backend, frontend) Docker-оор асна. Эхний удаа 5–10 минут болно.
3. **Ports** таб дээрх **3000** портын 🌐 дүрсийг дарж сайтаа нээнэ. Бусдад харуулах бол 3000 портын **Port Visibility → Public** болгоно. 8000 портыг нээх шаардлагагүй: frontend өөрөө backend рүү дамжуулна.
4. AI зөвлөгчийг асаах: https://console.groq.com дээрээс үнэгүй API key аваад `.env` файлд `GROQ_API_KEY=...` гэж оруулаад терминалд:

```bash
docker compose --env-file .env -f infra/docker-compose.yml up -d backend
```

### B. Өөрийн компьютер дээр (Docker Desktop)

```bash
git clone https://github.com/tsogto1/ubbbair.git
cd ubbbair
cp .env.example .env
docker compose --env-file .env -f infra/docker-compose.yml up -d --build
```

- Сайт: http://localhost:3000
- API docs: http://localhost:8000/docs
- Лог харах: `docker compose --env-file .env -f infra/docker-compose.yml logs -f backend`
- Унтраах: `docker compose --env-file .env -f infra/docker-compose.yml down`

`seed` сервис эхний асалтаар database migration-уудыг ажиллуулж, `data-pipeline/unegui_listings.json` болон үерийн бүсийн GeoJSON-оос жишээ өгөгдөл оруулна. Дахин асаахад давхардуулахгүй.

### C. Онлайн байршуулах (Vercel + Railway + Neon)

1. **Database — Neon**: шинэ project үүсгээд SQL Editor дээр `CREATE EXTENSION postgis; CREATE EXTENSION vector;` ажиллуулна. Connection string-ийг хуулж авна.
2. Migration + жишээ өгөгдөл: Codespace эсвэл өөрийн компьютерээс:

```bash
docker compose --env-file .env -f infra/docker-compose.yml run --rm --no-deps -e DATABASE_URL="<neon-url>" seed
```

3. **Backend — Railway**: repo-оо холбоод Root Directory = `backend`. Variables: `DATABASE_URL`, `REDIS_URL` (Railway Redis нэмнэ), `GROQ_API_KEY`, `LLM_PROVIDER=groq`. Dockerfile нь Railway-ийн `PORT`-ийг өөрөө уншина.
4. **Frontend — Vercel**: Root Directory = `frontend`, Environment Variable `API_URL=https://<railway-backend-url>`. `/api/*` болон `/uploads/*` хүсэлтүүд энэ хаяг руу дамжина.

Тэмдэглэл: Railway-д зөвхөн `backend` хавтас ордог тул `data-pipeline/output` доторх тусгай зөвшөөрлийн CSV-үүд онлайн хувилбарт ачаалагдахгүй. Хар жагсаалтын шалгалт Docker/Codespaces хувилбарт бүрэн ажиллана.

## Нууц болон админ тохиргоо

- `.env` нь зөвхөн локал тохиргоонд зориулагдсан бөгөөд Git-д орохгүй. `.env.example`-д бодит түлхүүр, нууц үг бүү оруул.
- PostgreSQL болон Redis-ийн портууд локал интерфэйст л холбогдоно.
- Шинэ хэрэглэгчдэд админ эрх автоматаар өгөхгүй. Өөрийн бүртгэлийг үүсгэсний дараа зөвшөөрөгдсөн админаар мэдээллийн санд эрхийг нь тусгайлан олгоно.
- Өмнө нь database үүсгэсэн бол хуучин seed админыг гараар устгана: `DELETE FROM users WHERE email = 'admin@example.com';`
- Шинэ password бүр өөрийн random salt ашиглана. Өмнөх хувилбарт бүртгүүлсэн хэрэглэгчид шинэ password тохируулах шаардлагатай.
- Нууц түлхүүр GitHub-д өмнө нь ил болсон бол `.env`-ээс устгах нь хангалтгүй; үйлчилгээ үзүүлэгч дээр хүчингүй болгож, шинэ түлхүүр үүсгэнэ.

## MVP-ийн дараалал

1. **1-р долоо хоног** — НХБХГ хар жагсаалт + барилгын зөвшөөрөл шалгалт
2. **2-р долоо хоног** — GIS эрсдэлийн зураглал (PostGIS + Mapbox)
3. **3-р долоо хоног** — AI зөвлөгч (Claude API + RAG)
4. **4-р долоо хоног** — Гэрээ үүсгэх, цахим гарын үсэг

## Хуулийн анхааруулга

Энэ систем нь **зөвлөгч** бөгөөд **баталгаа** биш. Аливаа
шийдвэр гаргахаасаа өмнө мэргэжлийн хуульч болон инженерт
хандахыг зөвлөж байна.
