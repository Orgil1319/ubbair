from contextlib import asynccontextmanager
import asyncio
import logging
import asyncpg
import redis.asyncio as aioredis
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import ai_advisor, ads, auth, blacklist, contracts, lease, notifications, price, properties, risk
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    for attempt in range(60):
        try:
            app.state.db = await asyncpg.create_pool(db_url)
            break
        except (OSError, asyncio.TimeoutError, asyncpg.PostgresError) as e:
            if attempt == 59:
                raise
            logger.warning(f"DB бэлэн болоогүй байна ({e}), 2 секундын дараа дахин оролдоно")
            await asyncio.sleep(2)
    app.state.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    logger.info("DB болон Redis холбогдлоо")
    yield
    # Shutdown
    await app.state.db.close()
    await app.state.redis.close()

app = FastAPI(
    title="Монголын Үл Хөдлөх Хөрөнгийн Зөвлөх API",
    description="Байрны эрсдэл, үнэ, гэрээний мэдээлэл",
    version="1.0.0",
    lifespan=lifespan,
)

allowed_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(',') if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(properties.router, prefix="/api", tags=["Байр"])
app.include_router(risk.router, prefix="/api/risk", tags=["Эрсдэл"])
app.include_router(price.router, prefix="/api", tags=["Үнэ"])
app.include_router(blacklist.router, prefix="/api", tags=["Хар жагсаалт"])
app.include_router(contracts.router, prefix="/api/contracts", tags=["Гэрээ"])
app.include_router(lease.router, prefix="/api", tags=["Түрээс"])
app.include_router(ai_advisor.router, prefix="/api/ai", tags=["AI Зөвлөгч"])
app.include_router(ads.router, prefix="/api/ads", tags=["Зар"])
app.include_router(notifications.router, prefix="/api", tags=["Сануулга"])

uploads_dir = Path(__file__).resolve().parents[1] / "uploads"
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "real-estate-advisor"}
