from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.claude_service import ClaudeService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
claude = ClaudeService()


class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    property_id: Optional[str] = None
    property_context: Optional[dict] = None


class LegalRequest(BaseModel):
    situation: str
    # Жишээ: "байрны эзэн мэдэгдэлгүйгээр гарахыг шаардаж байна"


class PriceExplainRequest(BaseModel):
    property_price: float
    area_sqm: float
    district: str
    market_data: dict


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Байрны зөвлөгчтэй чат. property_context байвал тухайн байрны мэдээлэлтэй хариулна.
    """
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        response = await claude.chat(messages, request.property_context)
        return {"response": response}
    except Exception as e:
        logger.error(f"AI chat алдаа: {e}")
        raise HTTPException(status_code=500, detail="AI зөвлөгч ажиллахад алдаа гарлаа")


@router.post("/legal-rights")
async def explain_legal_rights(request: LegalRequest):
    """
    Нөхцөл байдлаар түрээслэгчийн эрх, хуулийн мэдээлэл тайлбарлана.
    """
    try:
        explanation = await claude.explain_legal_rights(request.situation)
        return {"explanation": explanation}
    except Exception as e:
        logger.error(f"Хуулийн тайлбар алдаа: {e}")
        raise HTTPException(status_code=500, detail="Тайлбар авахад алдаа гарлаа")


@router.post("/price-explain")
async def explain_price(request: PriceExplainRequest):
    """
    Байрны үнийг зах зээлтэй харьцуулан AI тайлбар гаргана.
    """
    try:
        explanation = await claude.analyze_price_fairness(
            request.property_price,
            request.area_sqm,
            request.district,
            request.market_data,
        )
        return {"explanation": explanation}
    except Exception as e:
        logger.error(f"Үнийн тайлбар алдаа: {e}")
        raise HTTPException(status_code=500, detail="Үнийн тайлбар авахад алдаа гарлаа")
