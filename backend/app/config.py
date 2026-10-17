from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/realestate"
    REDIS_URL: str = "redis://localhost:6379"

    # AI
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"  # эсвэл "llama-3.3-70b-versatile"
    LLM_PROVIDER: str = "anthropic"   # "anthropic" | "ollama" | "groq"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"

    # RAG / vector DB
    CHROMA_DB_PATH: str = "./.chromadb"

    # Maps
    MAPBOX_TOKEN: str = ""

    # External data sources
    OPENDATA_API_URL: str = "https://opendata.gov.mn/api/3"
    NKHBHG_API_URL: str = "https://opendata.burtgel.gov.mn/api"

    # E-signature
    HELLOSIGN_API_KEY: str = ""

    # Email/Push notifications
    SENDGRID_API_KEY: str = ""

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,https://yourdomain.mn"
    LEGACY_PASSWORD_SALT: str = ""
    SESSION_TTL_HOURS: int = 24

    # Cache TTL (seconds)
    BLACKLIST_CACHE_TTL: int = 86400       # 1 өдөр
    PRICE_DATA_CACHE_TTL: int = 3600       # 1 цаг
    RISK_ZONE_CACHE_TTL: int = 604800      # 7 хоног

    # Data refresh
    DATA_REFRESH_INTERVAL_DAYS: int = 14  # 2 долоо хоног

    model_config = SettingsConfigDict(env_file=str(Path(__file__).resolve().parents[2] / ".env"), extra="ignore")


settings = Settings()
