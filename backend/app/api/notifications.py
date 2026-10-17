import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/notifications")
async def notifications():
    """Сануулга жагсаалт буцаана."""
    return {"items": []}
