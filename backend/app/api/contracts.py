from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from datetime import date
from typing import Optional
from app.api.auth import get_current_user
from app.services.contract_generator import ContractGenerator, ContractParty, LeaseContractData
import json
import logging
import uuid

router = APIRouter()
logger = logging.getLogger(__name__)
generator = ContractGenerator()

CONTRACT_COLUMNS = """
    id::text, contract_number, owner_name, owner_email, tenant_name, tenant_email,
    property_address, area_sqm, rooms, monthly_rent, deposit, start_date, end_date,
    owner_signed, tenant_signed, status, created_at
"""


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
    rooms: Optional[int] = None


def render_pdf(contract: ContractRequest, contract_number: str) -> bytes:
    data = LeaseContractData(
        owner=ContractParty(**contract.owner.model_dump()),
        tenant=ContractParty(**contract.tenant.model_dump()),
        property_address=contract.property_address,
        property_area_sqm=contract.property_area_sqm,
        monthly_rent=contract.monthly_rent,
        deposit=contract.deposit,
        start_date=contract.start_date,
        end_date=contract.end_date,
        payment_day=contract.payment_day,
        notice_days=contract.notice_days,
        contract_id=contract_number,
    )
    return generator.generate(data)


def pdf_response(pdf_bytes: bytes, contract_number: str, contract_id: Optional[str] = None) -> Response:
    headers = {"Content-Disposition": f'attachment; filename="lease_contract_{contract_number}.pdf"'}
    if contract_id:
        headers["X-Contract-Id"] = contract_id
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


async def optional_user(request: Request) -> Optional[dict]:
    if not request.headers.get("Authorization", "").startswith("Bearer "):
        return None
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


def parse_contract_id(contract_id: str) -> str:
    try:
        return str(uuid.UUID(contract_id))
    except ValueError:
        raise HTTPException(status_code=404, detail="Гэрээ олдсонгүй")


def row_to_contract(row) -> dict:
    return {
        "id": row["id"],
        "contractNumber": row["contract_number"],
        "ownerName": row["owner_name"],
        "ownerEmail": row["owner_email"] or "",
        "tenantName": row["tenant_name"],
        "tenantEmail": row["tenant_email"] or "",
        "address": row["property_address"],
        "area": float(row["area_sqm"] or 0),
        "rooms": row["rooms"] or 0,
        "monthlyRent": str(row["monthly_rent"]),
        "deposit": str(row["deposit"]),
        "startDate": row["start_date"].isoformat(),
        "endDate": row["end_date"].isoformat(),
        "ownerSigned": bool(row["owner_signed"]),
        "tenantSigned": bool(row["tenant_signed"]),
        "status": row["status"],
        "createdAt": row["created_at"].isoformat(),
    }


async def save_contract(request: Request, contract: ContractRequest, contract_number: str) -> Optional[str]:
    user = await optional_user(request)
    try:
        async with request.app.state.db.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO contracts (
                    contract_number, user_id, owner_name, owner_register, owner_email, owner_phone,
                    tenant_name, tenant_register, tenant_email, tenant_phone, property_address,
                    area_sqm, rooms, monthly_rent, deposit, start_date, end_date, notice_days,
                    payment_day, request_data
                ) VALUES (
                    $1, $2::uuid, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16,
                    $17, $18, $19, $20::jsonb
                )
                RETURNING id::text
                """,
                contract_number,
                user["id"] if user else None,
                contract.owner.full_name,
                contract.owner.register_id,
                contract.owner.email,
                contract.owner.phone,
                contract.tenant.full_name,
                contract.tenant.register_id,
                contract.tenant.email,
                contract.tenant.phone,
                contract.property_address,
                contract.property_area_sqm,
                contract.rooms,
                contract.monthly_rent,
                contract.deposit,
                contract.start_date,
                contract.end_date,
                contract.notice_days,
                contract.payment_day,
                json.dumps(contract.model_dump(mode="json"), ensure_ascii=False),
            )
    except Exception as e:
        logger.error(f"Гэрээ хадгалахад алдаа: {e}")
        return None


@router.post("/generate-pdf")
async def generate_contract_pdf(request: Request, contract: ContractRequest):
    contract_number = f"LS-{uuid.uuid4().hex[:8].upper()}"
    try:
        pdf_bytes = render_pdf(contract, contract_number)
    except Exception as e:
        logger.error(f"Гэрээ үүсгэхэд алдаа: {e}")
        raise HTTPException(status_code=500, detail="Гэрээ үүсгэхэд алдаа гарлаа")
    contract_id = await save_contract(request, contract, contract_number)
    return pdf_response(pdf_bytes, contract_number, contract_id)


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


@router.get("")
async def list_contracts(request: Request):
    user = await get_current_user(request)
    async with request.app.state.db.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT {CONTRACT_COLUMNS} FROM contracts WHERE user_id = $1::uuid ORDER BY created_at DESC",
            user["id"],
        )
    return [row_to_contract(r) for r in rows]


@router.get("/{contract_id}")
async def get_contract(request: Request, contract_id: str):
    contract_id = parse_contract_id(contract_id)
    async with request.app.state.db.acquire() as conn:
        row = await conn.fetchrow(f"SELECT {CONTRACT_COLUMNS} FROM contracts WHERE id = $1::uuid", contract_id)
    if not row:
        raise HTTPException(status_code=404, detail="Гэрээ олдсонгүй")
    return row_to_contract(row)


@router.get("/{contract_id}/pdf")
async def get_contract_pdf(request: Request, contract_id: str):
    contract_id = parse_contract_id(contract_id)
    async with request.app.state.db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT contract_number, request_data FROM contracts WHERE id = $1::uuid", contract_id
        )
    if not row or not row["request_data"]:
        raise HTTPException(status_code=404, detail="Гэрээ олдсонгүй")
    contract = ContractRequest.model_validate(json.loads(row["request_data"]))
    try:
        pdf_bytes = render_pdf(contract, row["contract_number"])
    except Exception as e:
        logger.error(f"Гэрээний PDF үүсгэхэд алдаа: {e}")
        raise HTTPException(status_code=500, detail="Гэрээний PDF үүсгэхэд алдаа гарлаа")
    return pdf_response(pdf_bytes, row["contract_number"], contract_id)


@router.post("/{contract_id}/send-for-signing")
async def send_for_signing(request: Request, contract_id: str):
    contract_id = parse_contract_id(contract_id)
    async with request.app.state.db.acquire() as conn:
        updated = await conn.fetchval(
            "UPDATE contracts SET status = 'sent' WHERE id = $1::uuid RETURNING id::text", contract_id
        )
    if not updated:
        raise HTTPException(status_code=404, detail="Гэрээ олдсонгүй")
    return {"status": "sent", "emailSent": False}
