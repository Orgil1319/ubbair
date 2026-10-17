from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from datetime import date
from typing import Optional
from app.services.contract_generator import ContractGenerator, ContractParty, LeaseContractData
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
generator = ContractGenerator()


class PartyInput(BaseModel):
    full_name: str
    register_id: str
    phone: str
    email: Optional[str] = None
    address: str


class ContractRequest(BaseModel):
    owner: PartyInput
    tenant: PartyInput
    property_address: str
    property_area_sqm: float
    monthly_rent: int
    deposit: int
    start_date: date
    end_date: date
    payment_day: int = 1
    notice_days: int = 30


@router.post("/generate-pdf")
async def generate_contract_pdf(request: ContractRequest):
    """
    Гэрээний PDF үүсгэж буцаана.
    Иргэний хуулийн 318-р зүйлд нийцсэн загвар.
    """
    try:
        import uuid
        data = LeaseContractData(
            owner=ContractParty(**request.owner.model_dump()),
            tenant=ContractParty(**request.tenant.model_dump()),
            property_address=request.property_address,
            property_area_sqm=request.property_area_sqm,
            monthly_rent=request.monthly_rent,
            deposit=request.deposit,
            start_date=request.start_date,
            end_date=request.end_date,
            payment_day=request.payment_day,
            notice_days=request.notice_days,
            contract_id=f"LS-{uuid.uuid4().hex[:8].upper()}",
        )
        pdf_bytes = generator.generate(data)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="lease_contract_{data.contract_id}.pdf"'
            },
        )
    except Exception as e:
        logger.error(f"Гэрээ үүсгэхэд алдаа: {e}")
        raise HTTPException(status_code=500, detail="Гэрээ үүсгэхэд алдаа гарлаа")


@router.get("/template-checklist")
async def get_checklist():
    """
    Гэрээ байгуулахын өмнөх 5 минутын чек-лист.
    """
    return {
        "checklist": [
            {
                "id": 1,
                "question": "Гэрээг бичгээр байгуулж байна уу?",
                "law": "Иргэний хуулийн 318.1",
                "warning": "Аман гэрээ хүчин төгөлдөр бус — бичгээр байлгах заавал шаардлагатай",
            },
            {
                "id": 2,
                "question": "Гэрээг нотариатаар гэрчлүүлж байна уу?",
                "law": "Иргэний хуулийн 60",
                "warning": "Нотариатын баталгаагүй гэрээ маргаанд сул байна",
            },
            {
                "id": 3,
                "question": "Үл хөдлөх хөрөнгийн улсын бүртгэлд бүртгүүлэх үү?",
                "law": "Иргэний хуулийн 318.4",
                "warning": "Бүртгэлгүй гэрээ хүчин төгөлдөр бус гэж үзэгдэнэ",
            },
            {
                "id": 4,
                "question": "Эрт гарах нөхцөл (хугацаа, нөхөн төлбөр) гэрээнд тусгасан уу?",
                "law": "Иргэний хуулийн 204",
                "warning": "Тусгаагүй бол маргаан гарсан үед хамгаалал байхгүй",
            },
            {
                "id": 5,
                "question": "Барьцаа мөнгоны нөхцөл (хэмжээ, буцаах хугацаа) бичигдсэн үү?",
                "law": "Гэрээний чөлөөт зарчим",
                "warning": "Бичгээр тусгаагүй бол буцааж авах эрх хязгаарлагдана",
            },
        ]
    }
