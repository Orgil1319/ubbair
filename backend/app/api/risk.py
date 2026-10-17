from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from app.services.risk_engine import RiskEngine
from app.services.gis_service import GISService
from app.services.blacklist_checker import BlacklistChecker
from app.services.claude_service import ClaudeService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class RiskRequest(BaseModel):
    lat: float = Field(..., ge=40.0, le=52.0, description="Өргөрөг")
    lng: float = Field(..., ge=87.0, le=120.0, description="Уртраг")
    permit_id: Optional[str] = None
    developer_name: Optional[str] = None
    include_ai_explanation: bool = True


class RiskResponse(BaseModel):
    overall_score: int
    overall_level: str
    factors: list
    summary_mn: str
    ai_explanation: Optional[str] = None
    data_freshness_warning: bool
    assessed_at: str


@router.post("/assess", response_model=RiskResponse)
async def assess_risk(request: RiskRequest):
    """
    Байрны байршлаар бүрэн эрсдэлийн үнэлгээ хийнэ.
    GIS, хар жагсаалт, барилгын зөвшөөрлийг нэгтгэн дүгнэнэ.
    """
    try:
        # TODO: dependency injection-р солих
        # engine = RiskEngine(gis, blacklist, db)
        # assessment = await engine.assess(...)

        # Хялбаршуулсан тест хариу
        return RiskResponse(
            overall_score=75,
            overall_level="high",
            factors=[
                {
                    "type": "flood",
                    "level": "high",
                    "score": 75,
                    "title_mn": "🌊 Үерийн эрсдэлтэй бүс",
                    "description_mn": "Энэ байршил ОБЕГ-ын үерийн эрсдэлтэй бүсэд орж байна.",
                    "source": "ОБЕГ GIS дата",
                }
            ],
            summary_mn="Дунд зэргийн эрсдэлтэй байна. Мэргэжлийн үнэлгээ авахыг зөвлөж байна.",
            data_freshness_warning=False,
            assessed_at="2025-06-01T10:00:00",
        )
    except Exception as e:
        logger.error(f"Эрсдэл үнэлэхэд алдаа: {e}")
        raise HTTPException(status_code=500, detail="Эрсдэл үнэлэхэд алдаа гарлаа")


@router.get("/zones/{layer_name}")
async def get_risk_zones(
    layer_name: str,
    district: Optional[str] = Query(None, description="Дүүргийн нэр"),
):
    """
    Эрсдэлтэй бүсүүдийн GeoJSON өгөгдөл.
    """
    valid_layers = ["flood_risk_zones", "kindergartens", "schools", "hospitals"]
    if layer_name not in valid_layers:
        raise HTTPException(status_code=404, detail="Layer not found")

    import asyncpg
    import json
    from app.config import settings

    db_url = settings.DATABASE_URL.replace("+asyncpg", "")
    try:
        conn = await asyncpg.connect(db_url)
        query = f"""
        SELECT jsonb_build_object(
            'type',     'FeatureCollection',
            'features', COALESCE(jsonb_agg(features.feature), '[]'::jsonb)
        )
        FROM (
          SELECT jsonb_build_object(
            'type',       'Feature',
            'geometry',   ST_AsGeoJSON(geometry)::jsonb,
            'properties', to_jsonb(inputs) - 'geometry'
          ) AS feature
          FROM (SELECT * FROM {layer_name} LIMIT 3000) inputs
        ) features;
        """
        result = await conn.fetchval(query)
        await conn.close()

        if result:
            geojson = json.loads(result)
            geojson["metadata"] = {
                "source": "manaikhoroo.ub.gov.mn",
                "updated_at": "2026"
            }
            return geojson
            
    except Exception as e:
        logger.error(f"PostGIS-ээс өгөгдөл татахад алдаа: {e}")

    return {
        "type": "FeatureCollection",
        "features": [],
        "metadata": {
            "source": "manaikhoroo.ub.gov.mn",
            "updated_at": "2026",
        },
    }


@router.get("/{property_id}")
async def get_risk_assessment(property_id: str):
    """
    Байрны эрсдэлийн үнэлгээг propertyId-р авах (UI-д тохируулсан формат).
    """
    try:
        # TODO: Өгөгдлийн сангаас бодит мэдээлэл татах эсвэл RiskEngine ашиглах
        return {
            "propertyId": property_id,
            "score": 75,
            "level": "high",
            "items": [
                {
                    "type": "flood",
                    "label": "🌊 Үерийн эрсдэлтэй бүс",
                    "severity": "high",
                    "description": "Энэ байршил ОБЕГ-ын үерийн эрсдэлтэй бүсэд орж байна.",
                    "source": "ОБЕГ GIS дата",
                    "updatedAt": "2025-06-01T10:00:00",
                }
            ],
            "updatedAt": "2025-06-01T10:00:00",
        }
    except Exception as e:
        logger.error(f"Эрсдэл татахад алдаа: {e}")
        raise HTTPException(status_code=500, detail="Алдаа гарлаа")

