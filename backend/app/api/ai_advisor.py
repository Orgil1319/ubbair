from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.config import settings
from app.services.claude_service import ClaudeService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
_claude: Optional[ClaudeService] = None


def ai_configured() -> bool:
    if (settings.LLM_PROVIDER or "groq").lower() == "openai":
        return bool(settings.OPENAI_API_KEY)
    return bool(settings.GROQ_API_KEY)


def get_claude() -> ClaudeService:
    global _claude
    if not ai_configured():
        raise HTTPException(
            status_code=503,
            detail="AI зөвлөгч тохируулагдаагүй байна. .env файлд GROQ_API_KEY оруулаад backend-ээ дахин асаана уу.",
        )
    if _claude is None:
        _claude = ClaudeService()
    return _claude


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
    claude = get_claude()
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
    claude = get_claude()
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
    claude = get_claude()
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
