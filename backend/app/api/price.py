import logging

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/price/{property_id}")
async def get_price_analysis(property_id: str):
    """Үнийн шинжилгээний үндсэн хариу буцаана."""
    try:
        return {
            "propertyId": property_id,
            "districtAvgPerM2": 1_200_000,
            "cityAvgPerM2": 1_050_000,
            "comparables": [
                {"title": "Сүхбаатар дүүрэг, 2 өрөө", "price": 145_000_000, "area": 52, "district": "Сүхбаатар"},
                {"title": "Чингэлтэй дүүрэг, 3 өрөө", "price": 210_000_000, "area": 78, "district": "Чингэлтэй"},
            ],
            "updatedAt": "2026-06-15T00:00:00",
        }
    except Exception as exc:
        logger.error(f"Price analysis error: {exc}")
        raise HTTPException(status_code=500, detail="Price analysis error")
