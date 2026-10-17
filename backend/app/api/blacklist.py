import logging

from fastapi import APIRouter, HTTPException, Query, Request
from app.services.blacklist_checker import BlacklistChecker

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/blacklist/suggest")
async def suggest_companies(request: Request, q: str = Query(..., min_length=2)):
    """Autocomplete: компанийн нэрийг бичиж байх үед санал гаргана."""
    try:
        checker = BlacklistChecker(request.app.state.db, request.app.state.redis)
        suggestions = await checker.suggest(q)
        return {"suggestions": suggestions}
    except Exception as exc:
        logger.error(f"Suggest error: {exc}")
        raise HTTPException(status_code=500, detail="Suggest error")

@router.get("/blacklist/check")
async def check_blacklist(request: Request, q: str = Query(...)):
    """Компанийн хар жагсаалт шалгах API."""
    try:
        checker = BlacklistChecker(request.app.state.db, request.app.state.redis)
        result = await checker.check(q)
        # Wrap it in standard response if needed, or just return result
        return result
    except Exception as exc:
        logger.error(f"Blacklist check error: {exc}")
        raise HTTPException(status_code=500, detail="Blacklist check error")
